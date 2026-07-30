"""
jimureport_type_file_dataset.py — 文件数据集报表（Excel/CSV 上传 → 数据集）

特点：
  - 上传文件到 /jmreport/source/datasource/files/add（isSingle=true）
  - 调用 /dataset/files/single/save 创建 dbType="6" 数据集
  - dbCode 由后端生成（拼音），需通过 /field/tree/{reportId} 反查
  - children 字段绑定名取 `child['title']`（不是 fieldName）
  - 图表绑定时 dataType="files"（不是 "sql"）

JSON schema:
{
  "type": "file_dataset",
  "reportName": "员工信息报表",
  "file": {"localPath": "C:/data/emp.xlsx", "dbChName": "员工信息"},
  "table": {
    "title": "员工信息表",
    "columns": [                       // field 必须与 Excel 列对应的拼音一致
      {"field": "xing_ming", "title": "姓名", "width": 100},
      {"field": "bu_men", "title": "部门", "width": 100}
    ]
  },
  "chart": {                            // 可选：dataType 自动设为 "files"
    "chartType": "bar.simple",
    "title": "...",
    "axisX": "xing_ming", "axisY": "salary"
  }
}

注意：
  - 用户提供本地文件路径，脚本自动上传
  - columns 的 field 必须用拼音（如「姓名」→ "xing_ming"），可先上传后用 /field/tree 反查
"""
import sys, os, mimetypes
sys.path.insert(0, os.path.dirname(__file__))

import json as _json

from jimureport_utils import Session, gen_id, make_designer, base_save, make_styles, print_summary
from jimureport_report import build_cols, build_table_rows


def _upload_file(session: Session, local_path: str, report_id: str) -> dict:
    """上传文件到 /jmreport/source/datasource/files/add，返回 result dict。
    注意：Excel/CSV 文件必须包含至少一行数据（纯表头会报"解析失败"）。
    """
    import requests as _req, urllib3 as _urllib3
    _urllib3.disable_warnings()
    fname = os.path.basename(local_path)
    ctype = mimetypes.guess_type(fname)[0] or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    token = session._s.headers.get("X-Access-Token") or session._s.headers.get("x-access-token")
    with open(local_path, "rb") as f:
        content = f.read()
    r = _req.post(
        f"{session.base_url}/source/datasource/files/add",
        headers={"X-Access-Token": token},
        files={"file": (fname, content, ctype)},
        data={"reportId": report_id, "isSingle": "true"},
        verify=False,
    )
    result = r.json()
    if not result.get("success"):
        raise RuntimeError(f"文件上传失败: {result.get('message')}")
    return result["result"]


def create_file_dataset_report(session: Session, config: dict) -> str:
    report_name = config["reportName"]
    file_cfg    = config["file"]
    table       = config.get("table", {})

    # ① orphan report_id + 上传文件
    report_id = gen_id()
    designer  = make_designer(report_id, report_name)
    upload    = _upload_file(session, file_cfg["localPath"], report_id)

    # ② 创建单文件数据集（dbType=6）
    save_data = {
        "reportId": report_id,
        "dbSource": {
            "id": upload["id"],
            "dbUrl": upload["dbUrl"],
            "dbChName": file_cfg.get("dbChName", "文件数据集"),
        },
    }
    session.request("/source/dataset/files/single/save", save_data)

    # ③ 反查 dbCode 和字段名（拼音）+ 中文显示名
    tree = session.get(f"/field/tree/{report_id}")
    db_code = None
    field_titles = []       # 真实绑定字段名（拼音）
    field_texts = {}        # 拼音 → 中文显示名（fieldText）
    for group in tree.get("result", []):
        items = group if isinstance(group, list) else [group]
        for item in items:
            if str(item.get("type", "")) == "6":
                db_code = item["code"]
                for child in item.get("children", []):
                    t = child["title"]
                    field_titles.append(t)
                    field_texts[t] = child.get("fieldText", t)
                break
        if db_code:
            break
    if not db_code:
        raise RuntimeError("未找到单文件数据集（dbType=6），上传可能失败")

    # ④ 构造表格布局：以文件实际解析出的字段为准
    # AI 给的 columns 字段名若全部命中真实字段才采用；否则用文件全部真实字段（拼音绑定 + 中文显示），
    # 避免 AI 猜的字段名（如 chan_pin_ming / ku_cun）对不上导致整列空白。
    ai_cols = table.get("columns", [])
    if ai_cols and all(c.get("field") in field_titles for c in ai_cols):
        cols_cfg = ai_cols
    else:
        cols_cfg = [{"field": t, "title": field_texts.get(t, t), "width": 100} for t in field_titles]

    # 标题单独构建（不交给 build_table_rows，避免它把标题放在 col0/A 并合并 A 列）
    table_cfg = {
        "datasetCode": db_code,
        "columns":     cols_cfg,
    }
    styles = make_styles()
    # make_styles 只有 0-4（0=标题 1=表头 2=数据）；build_table_rows 默认用 5/4/2 会引用不存在的 styles[5]
    # 导致前端整表渲染失败（空白）。显式传入 make_styles 实际存在的索引；表头/数据从第 2 行起，第 1 行放标题。
    rows, merges, _, _ = build_table_rows(table_cfg, start_row=2, title_style=0, header_style=1, data_style=2)
    # 标题行：从 B 列(col1)开始合并到最后一列，A 列(col0)留空——不合并 A 列
    n_cols = len(cols_cfg)
    last_letter = chr(ord("A") + n_cols)
    rows["1"] = {"height": 40, "cells": {
        "1": {"text": table.get("title", report_name), "style": 0, "merge": [0, n_cols - 1]}
    }}
    merges.append(f"B1:{last_letter}1")
    rows["len"] = 200
    cols = build_cols(cols_cfg)

    chart_list = []
    if config.get("chart"):
        from jimureport_utils import gen_layer, chart_entry
        ch = config["chart"]
        layer_id = gen_layer()
        next_row = max(int(k) for k in rows if k.isdigit()) + 11
        chart_list.append(chart_entry(
            layer_id=layer_id, db_id="", db_code=db_code,
            chart_type=ch["chartType"],
            echarts_cfg={"title": {"text": ch.get("title", ""), "left": "center"},
                         "tooltip": {}, "series": [{"type": ch["chartType"].split(".")[0], "data": []}]},
            row=next_row, col=1, col_end=len(cols_cfg),
            width=str(ch.get("width", 580)), height=str(ch.get("height", 320)),
            axis_x=ch.get("axisX", field_titles[0] if field_titles else "name"),
            axis_y=ch.get("axisY", field_titles[1] if len(field_titles) > 1 else "value"),
            data_type="files",
        ))

    session.request("/save", base_save(
        report_id, designer,
        rows=rows, cols=cols, styles=styles, merges=merges,
        chartList=chart_list,
    ))
    print_summary(report_id, report_name, session.base_url, "")
    return report_id
