"""
积木报表布局构建器 (jimureport_creator)

提供主题配色、表格/图表布局构建函数，供内联 heredoc 脚本 import 调用：
    from jimureport_creator import THEMES, get_theme, build_styles, build_cols,
                                   build_table_rows, build_chart_rows, build_echarts_config

也可作为独立 CLI 工具直接创建/编辑报表（通过 config.json 驱动）：
    python jimureport_creator.py --api-base <URL> --token <TOKEN> --config <config.json>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
config.json 示例（创建）:
{
    "action":     "create",
    "reportName": "登录日志统计报表",
    "theme":      "green",
    "pageSize":   10,
    "datasets": [
        {
            "dbCode":    "login_detail",
            "dbChName":  "登录日志明细",
            "dbDynSql":  "SELECT username, ip FROM sys_log WHERE log_type=1",
            "isPage":    "1"
        },
        {
            "dbCode":    "ip_daily",
            "dbChName":  "每日IP统计",
            "dbDynSql":  "SELECT DATE_FORMAT(...) AS name, COUNT(*) AS value, '' AS type ...",
            "isPage":    "0",
            "forChart":  true
        }
    ],
    "layout": "chart_bottom",
    "table": {
        "datasetCode": "login_detail",
        "title":       "登录日志统计报表",
        "columns": [
            {"field": "username", "title": "用户名", "width": 100},
            {"field": "ip",       "title": "IP地址",  "width": 120}
        ]
    },
    "chart": {
        "datasetCode": "ip_daily",
        "chartType":   "line.smooth",
        "title":       "最近10日每日访问IP总数",
        "width":       "680",
        "height":      "350"
    }
}

layout 可选值：table_only | chart_only | chart_top | chart_bottom | chart_right
theme  可选值：blue | green | orange | purple | red  或  {"primary":"#xxx","title":"#xxx"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import sys
import argparse

from jimureport_utils import (
    Session, gen_id, gen_layer, parse_sql, save_db,
    make_designer, base_save, get_report, print_summary,
)
from jimureport_datasource import resolve_ds_id, generate_sql_via_ai

# Windows 控制台中文
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# ── 主题配色 ─────────────────────────────────────────────────────────────

THEMES = {
    "blue":   {"primary": "#01b0f1", "title": "#333333", "chart": "#01b0f1", "area_rgba": "1,176,241"},
    "green":  {"primary": "#4CAF50", "title": "#333333", "chart": "#43A047", "area_rgba": "76,175,80"},
    "orange": {"primary": "#FF9800", "title": "#333333", "chart": "#F57C00", "area_rgba": "255,152,0"},
    "purple": {"primary": "#9C27B0", "title": "#333333", "chart": "#8E24AA", "area_rgba": "156,39,176"},
    "red":    {"primary": "#F44336", "title": "#333333", "chart": "#E53935", "area_rgba": "244,67,54"},
}

DEFAULT_CHART_COLORS = ["#5470c6", "#ee6666", "#91cc75", "#fac858", "#73c0de", "#3ba272", "#fc8452", "#9a60b4"]


def get_theme(config: dict) -> dict:
    """获取主题配色，支持预设名称或自定义对象。"""
    theme = config.get("theme", "blue")
    if isinstance(theme, dict):
        return {
            "primary":    theme.get("primary", "#01b0f1"),
            "title":      theme.get("title", "#333333"),
            "chart":      theme.get("chart", theme.get("primary", "#01b0f1")),
            "area_rgba":  theme.get("area_rgba", "1,176,241"),
        }
    return THEMES.get(theme, THEMES["blue"])


def build_styles(theme: dict) -> list:
    """根据主题生成标准 styles 列表（索引 0-5）。"""
    border = {"bottom": ["thin", "#d8d8d8"], "top": ["thin", "#d8d8d8"],
              "left":   ["thin", "#d8d8d8"], "right": ["thin", "#d8d8d8"]}
    return [
        {"border": border},                                                                    # 0 仅边框
        {"border": border, "align": "center"},                                                 # 1 边框+居中
        {"border": border, "align": "center", "valign": "middle"},                            # 2 数据行
        {"border": border, "align": "center", "valign": "middle", "bgcolor": theme["primary"]},              # 3
        {"border": border, "align": "center", "valign": "middle", "bgcolor": theme["primary"], "color": "#ffffff"},  # 4 表头
        {"align": "center", "valign": "middle", "font": {"bold": True, "size": 18}},          # 5 标题
    ]


# ── 布局构建 ─────────────────────────────────────────────────────────────

def _col_letter(idx: int) -> str:
    """列索引(1-based) → Excel列字母：1→B, 2→C（col 0 = A 留空）。"""
    return chr(ord("A") + idx)


def build_cols(columns: list) -> dict:
    """根据 columns 配置生成 cols 对象。"""
    cols: dict = {"len": 100}
    for i, col in enumerate(columns):
        if col.get("width"):
            cols[str(i + 1)] = {"width": col["width"]}
    return cols


def build_table_rows(
    table_config: dict,
    start_row: int = 1,
    title_style: int = 5,
    header_style: int = 4,
    data_style: int = 2,
) -> tuple[dict, list, int, dict]:
    """
    构造数据表格的 rows 和 merges。
    返回 (rows, merges, next_row, group_config)。

    columns 字段可选属性：
      group       True  → #{db.group(field)} 纵向分组
      funcname    "SUM" → 数据集聚合（SUM/COUNT/AVG）
      subtotalText      → 合计行标签，默认"合计"
      decimalPlaces     → 小数位数
    """
    rows: dict = {}
    merges: list = []
    columns = table_config.get("columns", [])
    ds_code  = table_config["datasetCode"]
    col_count = len(columns)
    row = start_row
    group_config: dict = {}

    # 标题行
    title = table_config.get("title")
    if title:
        rows[str(row)] = {"cells": {"0": {"text": title, "style": title_style,
                                          "merge": [0, col_count], "height": 50}}, "height": 50}
        ui_row = row + 1
        merges.append(f"A{ui_row}:{_col_letter(col_count)}{ui_row}")
        row += 1

    # 表头行
    rows[str(row)] = {"cells": {str(i + 1): {"text": col["title"], "style": header_style}
                                for i, col in enumerate(columns)}, "height": 34}
    row += 1

    # 数据绑定行
    data_cells: dict = {}
    for i, col in enumerate(columns):
        field = col["field"]
        cell: dict = {"style": data_style}
        if col.get("group"):
            cell["text"]         = f"#{{{ds_code}.group({field})}}"
            cell["aggregate"]    = "group"
            if "subtotalText" in col:
                cell["subtotal"]     = "groupField"
                cell["funcname"]     = "-1"
                cell["subtotalText"] = col["subtotalText"]
            if not group_config:
                group_config = {"isGroup": True, "groupField": f"{ds_code}.{field}"}
        elif col.get("funcname"):
            cell["text"]     = f"#{{{ds_code}.{field}}}"
            cell["subtotal"] = "-1"
            cell["funcname"] = col["funcname"]
            if col.get("decimalPlaces"):
                cell["decimalPlaces"] = col["decimalPlaces"]
        else:
            cell["text"] = f"#{{{ds_code}.{field}}}"
        data_cells[str(i + 1)] = cell

    rows[str(row)] = {"cells": data_cells}
    row += 1
    return rows, merges, row, group_config


def build_chart_rows(
    chart_config: dict,
    chart_db_id: str,
    theme: dict,
    start_row: int = 1,
    col_start: int = 1,
    col_end: int = 6,
    row_count: int = 1,
) -> tuple[dict, list, int]:
    """
    构造图表虚拟占位行和 chartList。
    返回 (rows, chart_list, next_row)。
    """
    layer_id = gen_layer()
    rows: dict = {}
    virtual_cell_range: list = []

    for r in range(start_row, start_row + row_count):
        rows[str(r)] = {"cells": {str(c): {"text": " ", "virtual": layer_id}
                                  for c in range(col_start, col_end + 1)}}
        for c in range(col_start, col_end + 1):
            virtual_cell_range.append([r, c])

    chart_type = chart_config.get("chartType", "bar.simple")
    chart_item = {
        "row":    start_row,
        "col":    col_start,
        "colspan": 0,
        "rowspan": 0,
        "width":  str(chart_config.get("width",  "650")),
        "height": str(chart_config.get("height", "350")),
        "config": json.dumps(build_echarts_config(chart_type, chart_config, theme), ensure_ascii=False),
        "url":    "",
        "extData": {
            "chartType": chart_type,
            "dataType":  chart_config.get("dataType", "sql"),
            "dataId":    chart_db_id,
            "dbCode":    chart_config["datasetCode"],
            "axisX":     "name",
            "axisY":     "value",
            "series":    "type",
            "xText":     "",
            "yText":     "",
            "apiStatus": "1",
        },
        "layer_id":         layer_id,
        "offsetX":          0,
        "offsetY":          0,
        "backgroud":        {"enabled": False, "color": "#fff", "image": ""},
        "virtualCellRange": virtual_cell_range,
    }
    return rows, [chart_item], start_row + row_count


def build_echarts_config(chart_type: str, chart_config: dict, theme: dict) -> dict:
    """根据图表类型构造最小 ECharts 配置。"""
    title_text = chart_config.get("title", "")
    colors     = chart_config.get("colors", [theme["chart"]] + DEFAULT_CHART_COLORS)
    area_rgba  = theme.get("area_rgba", "1,176,241")

    if chart_type.startswith("pie"):
        radius = ["40%", "70%"] if "doughnut" in chart_type else "70%"
        if "rose" in chart_type:
            radius = [20, "70%"]
        return {
            "title":   {"text": title_text, "left": "center", "textStyle": {"fontSize": 16}},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)",
                        "textStyle": {"color": "#fff", "fontSize": 14}},
            "legend":  {"orient": "vertical", "left": "left", "top": "middle"},
            "series":  [{"type": "pie", "radius": radius, "center": ["50%", "45%"],
                         "avoidLabelOverlap": True,
                         "itemStyle": {"borderRadius": 6, "borderColor": "#fff", "borderWidth": 2},
                         "label": {"show": True, "formatter": "{b}: {c} ({d}%)", "fontSize": 14},
                         "emphasis": {"label": {"show": True, "fontSize": 18, "fontWeight": "bold"}},
                         "data": [],
                         "roseType": "area" if "rose" in chart_type else None}],
            "color": colors,
        }
    if chart_type.startswith("bar"):
        is_h = "horizontal" in chart_type
        return {
            "title":   {"text": title_text, "left": "center"},
            "tooltip": {"trigger": "axis"},
            "legend":  {"bottom": 0},
            "xAxis":   {"show": True, "type": "value" if is_h else "category", "data": []},
            "yAxis":   {"show": True, "type": "category" if is_h else "value",  "data": []},
            "series":  [{"type": "bar", "data": [], "itemStyle": {"color": colors[0]}}],
            "color":   colors,
        }
    if chart_type.startswith("line"):
        smooth = "smooth" in chart_type
        return {
            "title":   {"text": title_text, "left": "center",
                        "textStyle": {"fontSize": 16, "color": theme["title"]}},
            "grid":    {"left": 60, "top": 60, "right": 40, "bottom": 60},
            "tooltip": {"show": True, "trigger": "axis"},
            "xAxis":   {"show": True, "type": "category", "data": []},
            "yAxis":   {"show": True, "type": "value", "minInterval": 1},
            "series":  [{"type": "line", "data": [], "smooth": smooth,
                         "lineStyle": {"width": 3, "color": theme["chart"]},
                         "itemStyle": {"color": theme["chart"]},
                         "areaStyle": {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                                                  "colorStops": [
                                                      {"offset": 0, "color": f"rgba({area_rgba},0.3)"},
                                                      {"offset": 1, "color": f"rgba({area_rgba},0.05)"},
                                                  ]}}}],
            "color": colors,
        }
    if chart_type.startswith("gauge"):
        return {"title": {"text": title_text, "left": "center"},
                "tooltip": {"formatter": "{b}: {c}"},
                "series": [{"type": "gauge", "data": [], "detail": {"formatter": "{value}"}}]}
    if chart_type.startswith("radar"):
        return {"title": {"text": title_text, "left": "center"}, "tooltip": {},
                "legend": {"bottom": 0}, "radar": {"indicator": []},
                "series": [{"type": "radar", "data": []}], "color": colors}
    if chart_type.startswith("funnel"):
        return {"title": {"text": title_text, "left": "center"},
                "tooltip": {"trigger": "item", "formatter": "{b}: {c}"},
                "legend": {"bottom": 0},
                "series": [{"type": "funnel", "data": [], "left": "10%", "width": "80%"}],
                "color": colors}
    if chart_type == "mixed.linebar":
        return {"title": {"text": title_text, "left": "center"},
                "tooltip": {"trigger": "axis"}, "legend": {"bottom": 0},
                "xAxis": {"show": True, "type": "category", "data": []},
                "yAxis": {"show": True, "type": "value"},
                "series": [{"type": "bar",  "data": []},
                           {"type": "line", "data": [], "smooth": True}],
                "color": colors}
    # fallback
    return {"title": {"text": title_text, "left": "center"}, "tooltip": {},
            "series": [{"type": "bar", "data": []}], "color": colors}


# ── 主流程（CLI 驱动） ────────────────────────────────────────────────────

def create_report(session: Session, config: dict) -> str | None:
    """创建新报表，返回 report_id。"""
    report_name = config["reportName"]
    theme  = get_theme(config)
    styles = build_styles(theme)
    print(f"\n{'=' * 50}\n创建积木报表: {report_name}\n{'=' * 50}")

    # Step 1: 客户端预生成 report_id（orphan，saveDb/link 接受）
    report_id = gen_id()
    designer  = make_designer(report_id, report_name)
    print(f"  report_id={report_id}")

    # Step 2: 解析并保存数据集（支持 SQL / API / JSON / 文件 / JavaBean / 共享）
    print("\n[1/3] 保存数据集...")
    dataset_ids: dict = {}
    # dbCode → chart extData dataType 字符串，供后续图表 dataType 自动修正使用
    # dbType: "0"=SQL "1"=API "2"=JavaBean "3"=JSON "4"=共享 "5"=文件(Calcite-SQL查询)
    _DBTYPE_TO_CHART = {"0":"sql","1":"api","2":"javabean","3":"json","4":"sql","5":"files"}
    dataset_chart_types: dict = {}
    for ds in config.get("datasets", []):
        db_code  = ds["dbCode"]
        db_type  = ds.get("dbType", "0")  # "0"=SQL, "3"=JSON

        if db_type == "3":
            # ── JSON 数据集 ──
            json_data = ds.get("jsonData", [])
            fl = ds.get("fieldList", [])
            # 简写支持：fieldList 可以是 [{"fieldName":"x","fieldText":"X"},...]
            # 也可以是 [["x","X"], ...] 简写格式
            if fl and isinstance(fl[0], (list, tuple)):
                fl = [{"fieldName":f,"fieldText":t,"widgetType":"String","orderNum":i,
                       "tableIndex":0,"extJson":"","dictCode":""} for i,(f,t) in enumerate(fl)]
            save_body = {
                "izSharedSource": 0, "jimuReportId": report_id,
                "dbCode": db_code, "dbChName": ds.get("dbChName", db_code),
                "dbType": "3", "dbSource": "", "isList": ds.get("isList", "1"),
                "isPage": ds.get("isPage", "0"), "dbDynSql": "",
                "jsonData": json.dumps({"data": json_data}, ensure_ascii=False),
                "apiConvert": "", "fieldList": fl, "paramList": ds.get("paramList", []),
            }
            resp = session.request("/saveDb", save_body)
            ds_id = resp["result"]["id"]
            print(f"  [{db_code}] JSON数据集 OK  id={ds_id}  records={len(json_data)}")
            dataset_chart_types[db_code] = "json"
        elif db_type == "1":
            # ── API 数据集 ──
            api_url = ds.get("apiUrl", ds.get("dbDynSql", ""))
            fl = ds.get("fieldList") or []
            if fl and isinstance(fl[0], (list, tuple)):
                fl = [{"fieldName":f,"fieldText":t,"widgetType":"String","orderNum":i,
                       "tableIndex":0,"extJson":"","dictCode":""} for i,(f,t) in enumerate(fl)]
            ds_id = save_db(session, report_id, db_code,
                            ds.get("dbChName", db_code), api_url, fl,
                            ds.get("paramList") or None,
                            db_type="1", api_url=api_url,
                            api_method=ds.get("apiMethod", "0"),
                            is_list=ds.get("isList", "1"),
                            is_page=ds.get("isPage", "1"))
            print(f"  [{db_code}] API数据集 OK  id={ds_id}")
            dataset_chart_types[db_code] = "api"
        elif db_type == "2":
            # ── JavaBean 数据集 ──
            java_value = ds.get("javaValue", ds.get("dbDynSql", ""))
            fl = ds.get("fieldList") or []
            if fl and isinstance(fl[0], (list, tuple)):
                fl = [{"fieldName":f,"fieldText":t,"widgetType":"String","orderNum":i,
                       "tableIndex":0,"extJson":"","dictCode":""} for i,(f,t) in enumerate(fl)]
            if not fl:
                # 自动调 /queryFieldByBean 获取字段列表
                r = session.request("/queryFieldByBean",
                                    {"javaType": "spring-key", "javaValue": java_value})
                fl = r.get("result", [])
            ds_id = save_db(session, report_id, db_code,
                            ds.get("dbChName", db_code), java_value, fl,
                            ds.get("paramList") or None,
                            db_type="2",
                            java_type="spring-key", java_value=java_value,
                            is_list=ds.get("isList", "1"),
                            is_page=ds.get("isPage", "0"))
            print(f"  [{db_code}] JavaBean数据集 OK  id={ds_id}  bean={java_value}")
            dataset_chart_types[db_code] = "javabean"
        elif db_type in ("es", "mongo", "mongodb", "redis"):
            # ── NoSQL 数据集（ES / MongoDB / Redis）── 实际保存类型均为 SQL ("0")
            # Calcite schema 前缀：es→"es."  mongo/mongodb→"mongo."  redis→无前缀
            import re as _re
            _SCHEMA   = {"es": "es",    "mongo": "mongo", "mongodb": "mongo", "redis": None}
            _IDX_KEY  = {"es": "esIndex", "mongo": "mongoCollection", "mongodb": "mongoCollection", "redis": None}
            schema    = _SCHEMA[db_type]
            idx_key   = _IDX_KEY[db_type]
            idx       = ds.get(idx_key, "") if idx_key else ""
            sql       = ds.get("dbDynSql", "")

            if idx and not sql:
                # 简写字段（esIndex / mongoCollection）→ 自动生成 SELECT *
                prefix = f"{schema}." if schema else ""
                sql = f"SELECT * FROM {prefix}{idx}"
            elif sql and schema and not _re.search(rf'(?i)\bFROM\s+{schema}\.', sql):
                # SQL 有但缺少 schema 前缀，自动注入
                sql = _re.sub(r'(?i)(FROM\s+)(\w+)', rf'\1{schema}.\2', sql, count=1)

            db_source = resolve_ds_id(session, ds.get("dbSource", ""))
            label = db_type.upper()
            print(f"  解析 [{db_code}] ({label}): {sql[:70]}{'...' if len(sql) > 70 else ''}")
            fl = parse_sql(session, sql, db_source)
            for f in fl:
                if f["fieldName"] in ds.get("fieldTextMap", {}):
                    f["fieldText"] = ds["fieldTextMap"][f["fieldName"]]
            ds_id = save_db(session, report_id, db_code,
                            ds.get("dbChName", db_code), sql, fl,
                            ds.get("paramList") or None,
                            db_type="0",
                            db_source=db_source,
                            is_list=ds.get("isList", "1"),
                            is_page=ds.get("isPage", "1"))
            print(f"  [{db_code}] {label}数据集 OK  id={ds_id}")
            dataset_chart_types[db_code] = "sql"

        else:
            # ── SQL 数据集 ──
            db_source = resolve_ds_id(session, ds.get("dbSource", ""))
            sql = ds.get("dbDynSql", "")
            # 只给了自然语言 requirement、没给 SQL → 调内置 AI 接口按真实表 DDL 生成 SQL
            if not sql and ds.get("requirement"):
                sql = generate_sql_via_ai(session, db_source, ds["requirement"])
                print(f"  [{db_code}] AI 生成 SQL: {sql[:80]}{'...' if len(sql) > 80 else ''}")
            print(f"  解析 [{db_code}]: {sql[:60]}{'...' if len(sql) > 60 else ''}")
            fl = parse_sql(session, sql, db_source)
            for f in fl:
                if f["fieldName"] in ds.get("fieldTextMap", {}):
                    f["fieldText"] = ds["fieldTextMap"][f["fieldName"]]
            ds_id = save_db(session, report_id, db_code,
                            ds.get("dbChName", db_code), sql, fl,
                            ds.get("paramList") or None,
                            db_source=db_source,
                            is_list=ds.get("isList", "1"),
                            is_page=ds.get("isPage", "1"))
            print(f"  [{db_code}] SQL数据集 OK  id={ds_id}")
            dataset_chart_types[db_code] = "sql"

        dataset_chart_types.setdefault(db_code, _DBTYPE_TO_CHART.get(str(db_type), "sql"))
        dataset_ids[db_code] = ds_id

    # Step 3: 构造布局
    print("\n[2/3] 构造报表布局...")
    layout       = config.get("layout", "table_only")
    table_config = config.get("table")
    chart_config = config.get("chart")
    all_rows: dict = {"len": 200}
    all_merges: list = []
    chart_list: list = []
    group_config: dict = {}
    col_count = len(table_config["columns"]) if table_config else 6

    def _add_chart(start: int, c_start: int = 1, c_end: int = None):
        nonlocal chart_list
        c_end = c_end or col_count
        c_db_id = dataset_ids.get(chart_config["datasetCode"], "")
        c_rows, cl, next_r = build_chart_rows(chart_config, c_db_id, theme, start, c_start, c_end)
        all_rows.update(c_rows)
        chart_list = cl
        return next_r

    if layout == "chart_top" and chart_config and table_config:
        next_row = _add_chart(1)
        all_rows[str(next_row)] = {"cells": {}, "height": 10}
        t_rows, t_merges, _, group_config = build_table_rows(table_config, next_row + 1)
        all_rows.update(t_rows); all_merges.extend(t_merges)
        print(f"  布局: 图表在上 + 数据表")

    elif layout == "chart_bottom" and chart_config and table_config:
        t_rows, t_merges, next_row, group_config = build_table_rows(table_config)
        all_rows.update(t_rows); all_merges.extend(t_merges)
        page_size = config.get("pageSize", 10)
        chart_start = (next_row - 1) + page_size + config.get("gap", 1)
        _add_chart(chart_start)
        all_rows[str(chart_start + page_size + 3)] = {"cells": {"1": {"text": " "}}}
        print(f"  布局: 数据表 + 图表在下")

    elif layout == "chart_right" and chart_config and table_config:
        t_rows, t_merges, _, group_config = build_table_rows(table_config)
        all_rows.update(t_rows); all_merges.extend(t_merges)
        c_start = col_count + 2
        c_rows, chart_list, _ = build_chart_rows(
            chart_config, dataset_ids.get(chart_config["datasetCode"], ""),
            theme, 1, c_start, c_start + 5)
        for k, v in c_rows.items():
            if k in all_rows and k != "len":
                all_rows[k]["cells"].update(v["cells"])
            else:
                all_rows[k] = v
        print(f"  布局: 数据表在左 + 图表在右")

    elif layout == "chart_only" and chart_config:
        _add_chart(1, 1, 6)
        print(f"  布局: 仅图表")

    elif table_config and config.get("charts"):
        # 表格 + 多图表（chart_linkage 场景）
        t_rows, t_merges, next_row, group_config = build_table_rows(table_config)
        all_rows.update(t_rows); all_merges.extend(t_merges)
        cur_row = next_row + 1
        for ch_cfg in config["charts"]:
            ch_db_id = dataset_ids.get(ch_cfg["datasetCode"], "")
            saved_chart_config = chart_config
            chart_config = ch_cfg
            c_rows, c_list, next_r = build_chart_rows(ch_cfg, ch_db_id, theme, cur_row, 1, col_count)
            chart_config = saved_chart_config
            all_rows.update(c_rows)
            chart_list.extend(c_list)
            cur_row = next_r + int(ch_cfg.get("height", 350)) // 25 + 2
        all_rows[str(cur_row + 5)] = {"cells": {"1": {"text": " "}}}
        print(f"  布局: 数据表 + {len(config['charts'])} 个图表")

    elif table_config:
        t_rows, t_merges, _, group_config = build_table_rows(table_config)
        all_rows.update(t_rows); all_merges.extend(t_merges)
        print(f"  布局: 仅数据表")

    else:
        print("  错误: 未配置 table 或 chart"); return None

    # 自定义 rows/merges 覆盖（复杂表头场景：跳过 build_table_rows，直接传完整 rows）
    if "customRows" in config:
        all_rows = config["customRows"]
        all_merges = config.get("customMerges", [])
        chart_list = config.get("customChartList", chart_list)
        gf = config.get("groupField")
        if gf:
            group_config = {"isGroup": True, "groupField": gf}
        print(f"  布局: 自定义 rows（{len(all_rows)} 行, {len(all_merges)} 合并）")

    # 自定义 styles 覆盖
    if "customStyles" in config:
        styles = config["customStyles"]

    # 自定义 cols 覆盖
    if "customCols" in config:
        cols = config["customCols"]
    else:
        cols = build_cols(table_config["columns"]) if table_config else {"len": 100}
    total_w = sum(v["width"] for v in cols.values() if isinstance(v, dict) and "width" in v)

    # Step 3.5: 钻取/联动（在 /save 之前创建 link，把 link_id 回填到 rows/chartList）
    drilling_links: dict = {}   # field → link_id
    linkage_links: list = []    # ordered list of link_ids
    if config.get("drilling"):
        for d in config["drilling"]:
            param_list = [{"paramName": p["paramName"],
                           "paramValue": p.get("paramValue", p.get("fieldName", "")),
                           "tableIndex": p.get("tableIndex", 0),
                           "dbCode": p.get("dbCode", table_config["datasetCode"] if table_config else ""),
                           "fieldName": p.get("fieldName", "")}
                          for p in d.get("params", [])]
            link_type = d.get("linkType", "0")
            target_report = d.get("targetReportId", report_id if link_type == "1" else "")
            payload = {
                "reportId":    target_report or report_id,
                "linkName":    d.get("name", "钻取"),
                "linkType":    link_type,
                "ejectType":   d.get("ejectType", "0"),
                "apiUrl":      d.get("targetUrl", ""),
                "apiMethod":   "",
                "requirement": "",
                "linkChartId": "",
                "parameter":   json.dumps(param_list, ensure_ascii=False),
            }
            r = session.request("/link/saveAndEdit", payload)
            link_id = r["result"]
            src = d.get("source", {})
            key = src.get("field") or src.get("chartIndex")
            drilling_links[(src.get("type", "cell"), key)] = link_id

    if config.get("linkages"):
        for lk in config["linkages"]:
            target = lk.get("target", {})
            target_layer = target.get("layerId") or ""
            # 通过 chartIndex 反查 layer_id
            if not target_layer and "chartIndex" in target:
                idx = target["chartIndex"]
                if idx < len(chart_list):
                    target_layer = chart_list[idx].get("layer_id", "")
            param_list = []
            for p in lk.get("params", []):
                item = {"paramName": p["paramName"],
                        "paramValue": p.get("paramValue", "")}
                if "fieldName" in p:
                    item.update({"tableIndex": p.get("tableIndex", 0),
                                 "dbCode": p.get("dbCode", ""),
                                 "fieldName": p["fieldName"]})
                else:
                    item["index"] = p.get("index", 1)
                param_list.append(item)
            payload = {
                "reportId":    report_id,
                "linkName":    lk.get("name", "联动"),
                "linkType":    "2",
                "ejectType":   "0",
                "apiUrl":      "", "apiMethod": "", "requirement": "",
                "linkChartId": target_layer,
                "parameter":   json.dumps(param_list, ensure_ascii=False),
            }
            r = session.request("/link/saveAndEdit", payload)
            linkage_links.append({"link_id": r["result"], "config": lk})

    # 把 drilling/linkage 的 link_id 回填到 rows 和 chartList
    if drilling_links and table_config:
        for r_idx, r_obj in all_rows.items():
            if r_idx == "len" or not isinstance(r_obj, dict):
                continue
            for c_idx, cell in r_obj.get("cells", {}).items():
                if not isinstance(cell, dict):
                    continue
                text = cell.get("text", "")
                for (src_type, src_key), lid in drilling_links.items():
                    if src_type == "cell" and src_key and f".{src_key}}}" in text:
                        cell["linkIds"] = lid
                        cell["display"] = "link"
    if drilling_links and chart_list:
        for ch in chart_list:
            for (src_type, src_key), lid in drilling_links.items():
                if src_type == "chart":
                    ch["extData"]["linkIds"] = lid
    if linkage_links:
        # 回填表格触发 / 图表触发
        for entry in linkage_links:
            lk = entry["config"]
            lid = entry["link_id"]
            src = lk.get("source", {})
            if src.get("type") == "cell" and table_config:
                fld = src.get("field")
                for r_idx, r_obj in all_rows.items():
                    if r_idx == "len" or not isinstance(r_obj, dict):
                        continue
                    for c_idx, cell in r_obj.get("cells", {}).items():
                        if isinstance(cell, dict) and fld and f".{fld}}}" in cell.get("text", ""):
                            prev = cell.get("linkIds", "")
                            cell["linkIds"] = (prev + "," + lid) if prev else lid
                            cell["display"] = "link"
            elif src.get("type") == "chart":
                idx = src.get("chartIndex", 0)
                if idx < len(chart_list):
                    ext = chart_list[idx]["extData"]
                    prev = ext.get("linkIds", "")
                    ext["linkIds"] = (prev + "," + lid) if prev else lid

    # Step 3.6: 图表 dataType 自动修正（按数据集实际类型覆盖默认 "sql"）
    for ch in chart_list:
        ext = ch.get("extData", {})
        ds_code_ref = ext.get("dbCode", "")
        if ds_code_ref in dataset_chart_types:
            ext["dataType"] = dataset_chart_types[ds_code_ref]

    # Step 3.7: 报表参数查询自动开启查询条
    param_total = sum(len(ds.get("paramList") or []) for ds in config.get("datasets", []))
    query_setting = {"izOpenQueryBar": True, "izDefaultQuery": True} if param_total > 0 else None

    # Step 4: 保存完整报表
    print("\n[3/3] 保存报表设计...")
    save_extra = {
        "rows": all_rows, "cols": cols, "styles": styles, "merges": all_merges,
        "chartList": chart_list, "dataRectWidth": total_w or 700,
    }
    if group_config:
        save_extra.update({"isGroup": True, "groupField": group_config["groupField"]})
    if query_setting:
        save_extra["querySetting"] = query_setting
    for k in ("imgList", "barcodeList", "qrcodeList", "loopBlockList",
              "zonedEditionList", "freeze", "freezeLineColor", "background",
              "rpbar", "printConfig",
              "displayConfig", "hiddenCells",
              "fixedPrintHeadRows", "fixedPrintTailRows",
              "completeBlankRowList", "dbexps", "autofilter"):
        if k in config:
            save_extra[k] = config[k]
    session.request("/save", base_save(report_id, designer, **save_extra))

    print_summary(report_id, report_name, session.base_url, "")
    return report_id


def edit_report(session: Session, config: dict) -> str | None:
    """编辑已有报表（GET → 改 → save）。"""
    report_id = config["reportId"]
    print(f"\n{'=' * 50}\n编辑积木报表: {report_id}\n{'=' * 50}")

    designer, design = get_report(session, report_id)
    report_name = config.get("reportName", designer.get("name", ""))
    theme  = get_theme(config)
    mods   = config.get("modifications", {})

    # 修改样式
    if "theme" in config:
        design["styles"] = build_styles(theme)

    # 修改图表配色
    if mods.get("updateChartTheme"):
        for chart in design.get("chartList", []):
            ec = json.loads(chart["config"])
            ct = chart.get("extData", {}).get("chartType", "")
            chart["config"] = json.dumps(
                build_echarts_config(ct, {"title": ec.get("title", {}).get("text", ""),
                                          "datasetCode": chart.get("extData", {}).get("dbCode", "")},
                                     theme), ensure_ascii=False)

    # 修改 merges / rows
    if "merges" in mods:
        design["merges"] = mods["merges"]
    for k, v in mods.get("rows", {}).items():
        design["rows"][k] = v

    session.request("/save", base_save(
        report_id, designer,
        rows=design["rows"], cols=design["cols"],
        styles=design["styles"], merges=design["merges"],
        chartList=design.get("chartList", []),
        isGroup=design.get("isGroup", False),
        groupField=design.get("groupField", ""),
    ))
    print_summary(report_id, report_name, session.base_url, "")
    return report_id


def main():
    parser = argparse.ArgumentParser(description="积木报表创建/编辑工具")
    parser.add_argument("--api-base", required=True, help="JeecgBoot 后端地址，如 http://192.168.x.x:8085")
    parser.add_argument("--token",    required=True, help="X-Access-Token")
    parser.add_argument("--config",   required=True, help="配置文件路径 (JSON)")
    args = parser.parse_args()

    base = args.api_base.rstrip("/")
    if not base.endswith("/jmreport"):
        base += "/jmreport"
    session = Session(base, args.token)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    action = config.get("action", "create")
    if action in ("create", "param_query"):
        # paramList 已由 create_report 透传 + querySetting 自动开启
        # drilling/linkages 键也在 create_report 内部处理（无需额外 Python 脚本）
        create_report(session, config)
    elif action == "edit":
        edit_report(session, config)
    elif action == "group":
        from jimureport_type_group import create_group_report
        create_group_report(session, config)
    elif action == "horizontal_group":
        from jimureport_type_hgroup import create_hgroup_report
        create_hgroup_report(session, config)
    elif action == "mastersub":
        from jimureport_type_mastersub import create_mastersub_report
        create_mastersub_report(session, config)
    elif action == "loopblock":
        from jimureport_type_loopblock import create_loopblock_report
        create_loopblock_report(session, config)
    elif action == "fillform":
        from jimureport_type_fillform import create_fillform_report
        create_fillform_report(session, config)
    elif action == "multilevel":
        from jimureport_type_multilevel import create_multilevel_report
        create_multilevel_report(session, config)
    elif action == "multisource":
        from jimureport_type_multisource import create_multisource_report
        create_multisource_report(session, config)
    elif action == "multisheet":
        from jimureport_type_multisheet import create_multisheet_report
        create_multisheet_report(session, config)
    elif action == "zoned":
        from jimureport_type_zoned import create_zoned_report
        create_zoned_report(session, config)
    elif action == "chart_linkage":
        from jimureport_type_chart_linkage import create_chart_linkage_report
        create_chart_linkage_report(session, config)
    elif action == "drilling":
        from jimureport_type_drilling import create_drilling_report
        create_drilling_report(session, config)
    elif action == "template_print":
        from jimureport_type_template_print import create_template_print_report
        create_template_print_report(session, config)
    elif action == "file_dataset":
        from jimureport_type_file_dataset import create_file_dataset_report
        create_file_dataset_report(session, config)
    else:
        print(f"未知操作类型: {action}"); sys.exit(1)


if __name__ == "__main__":
    main()
