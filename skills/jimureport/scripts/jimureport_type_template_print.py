"""
jimureport_type_template_print.py — 套打报表（背景图叠印 + 单条绑定）

特点：
  - 数据集 isPage="0" isList="0"，绑定用 `${db.field}`（单条），不是 `#{db.field}`
  - 背景图通过 imgList 传递（不是 printConfig.bgImg），同时 isBackend=True commonBackend=True
  - printConfig.isBackend=True，background=False（避免普通背景遮挡）
  - 用户必须先上传背景图，提供完整 URL（或本地路径，脚本自动上传）

JSON schema:
{
  "type": "template_print",
  "reportName": "发货单套打",
  "datasets": [{
    "dbCode": "order", "dbDynSql": "SELECT * FROM orders WHERE id='${orderId}'",
    "isPage": "0", "isList": "0",
    "paramList": [{"paramName":"orderId","paramValue":"","widgetType":"String","orderNum":1,"searchFlag":1,"searchMode":1}]
  }],
  "bgImage": {
    "url": "http://minio.xxx/bg.jpg",     // 或 "localPath": "C:/path/to/bg.jpg"
    "width": 950, "height": 683,
    "cols": 7, "rows": 15
  },
  "paper": "A4", "layout": "landscape",   // 可选，默认 A4 横向
  "cells": [
    {"row": 3, "col": 4, "field": "order_no",   "style": {"font": {"size": 14}}},
    {"row": 4, "col": 4, "field": "customer"},
    {"row": 5, "col": 4, "field": "address"}
  ]
}
"""
import sys, os, random, string, mimetypes
sys.path.insert(0, os.path.dirname(__file__))

from jimureport_utils import (
    Session, gen_id, parse_sql, save_db, make_designer, base_save,
    make_styles, print_summary,
)


def _gen_layer_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


def _upload_image(session: Session, local_path: str) -> str:
    """上传图片到 /upload（jimureport 自身端点），返回可直接使用的 URL。
    OSS 场景返回完整 https URL；本地存储返回 {base_url}/img/{msg} 路径。
    """
    fname = os.path.basename(local_path)
    ctype = mimetypes.guess_type(fname)[0] or "image/jpeg"
    with open(local_path, "rb") as f:
        content = f.read()
    result = session.upload("/upload", files={"file": (fname, content, ctype)})
    if not result.get("success"):
        raise RuntimeError(f"上传失败: {result.get('message')}")
    msg = result["message"]
    return msg if msg.startswith("http") else f"{session.base_url}/img/{msg}"


def create_template_print_report(session: Session, config: dict) -> str:
    report_name = config["reportName"]
    bg          = config["bgImage"]
    cells_cfg   = config.get("cells", [])

    # ① 上传背景图（如有 localPath）
    img_url = bg.get("url")
    if not img_url and bg.get("localPath"):
        img_url = _upload_image(session, bg["localPath"])
    if not img_url:
        raise ValueError("bgImage.url 或 bgImage.localPath 至少需提供一个")

    n_cols = bg.get("cols", 7)
    n_rows = bg.get("rows", 15)
    width  = bg.get("width", 950)
    height = bg.get("height", 683)

    # ② orphan id + 保存数据集（${db.field} 单条绑定，isPage/isList 都=0）
    report_id = gen_id()
    designer  = make_designer(report_id, report_name)
    dataset_ids = {}
    for ds in config.get("datasets", []):
        sql = ds.get("dbDynSql", "")
        fl  = parse_sql(session, sql, ds.get("dbSource", ""))
        for f in fl:
            if f["fieldName"] in ds.get("fieldTextMap", {}):
                f["fieldText"] = ds["fieldTextMap"][f["fieldName"]]
        ds_id = save_db(session, report_id, ds["dbCode"],
                        ds.get("dbChName", ds["dbCode"]), sql, fl,
                        ds.get("paramList") or None,
                        db_source=ds.get("dbSource", ""),
                        is_list=ds.get("isList", "0"),
                        is_page=ds.get("isPage", "0"))
        dataset_ids[ds["dbCode"]] = ds_id

    # ③ 构造 rows（每个数据单元格 ${db.field}），imgList 背景
    styles = make_styles()
    rows = {"len": 200, "0": {"cells": {}, "height": 25}}
    layer_id = _gen_layer_id()
    # row0 每个单元格挂 virtual 键
    for c in range(n_cols):
        rows["0"]["cells"][str(c)] = {"text": " ", "style": 0, "virtual": layer_id}

    # 数据绑定单元格
    ds_default = config.get("datasets", [{}])[0].get("dbCode", "")
    for cell_cfg in cells_cfg:
        r_str = str(cell_cfg["row"])
        c_str = str(cell_cfg["col"])
        if r_str not in rows:
            rows[r_str] = {"cells": {}, "height": cell_cfg.get("rowHeight", 25)}
        db_code = cell_cfg.get("dbCode", ds_default)
        field = cell_cfg["field"]
        cell = {"text": f"${{{db_code}.{field}}}"}
        if "style" in cell_cfg:
            cell["style"] = cell_cfg["style"]
        rows[r_str]["cells"][c_str] = cell

    img_entry = {
        "row": 0, "col": 0,
        "colspan": n_cols, "rowspan": n_rows,
        "width":  f"{width}px",
        "height": f"{height}px",
        "src": img_url,
        "isBackend": True,
        "commonBackend": True,
        "layer_id": layer_id,
        "offsetX": 0, "offsetY": 0,
        "virtualCellRange": [[0, c] for c in range(n_cols)],
    }

    cols = {"len": 100, "0": {"width": 20}}
    for c in range(1, n_cols + 1):
        cols[str(c)] = {"width": width // n_cols}

    print_cfg = {
        "paper": config.get("paper", "A4"),
        "width": 297 if config.get("layout", "landscape") == "landscape" else 210,
        "height": 210 if config.get("layout", "landscape") == "landscape" else 297,
        "definition": 1,
        "isBackend": True,
        "bgImg": "",
        "marginX": 0, "marginY": 0,
        "layout": config.get("layout", "landscape"),
        "printCallBackUrl": "",
    }

    session.request("/save", base_save(
        report_id, designer,
        rows=rows, cols=cols, styles=styles, merges=[],
        chartList=[], imgList=[img_entry],
        printConfig=print_cfg, background=False,
    ))
    print_summary(report_id, report_name, session.base_url, "")
    return report_id
