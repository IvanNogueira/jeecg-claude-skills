"""
jimureport_type_hgroup.py — 横向分组报表

两种模式，由 rowFields 是否存在决定：
  - 有 rowFields → 纵横组合：行头用 group()，列头用 groupRight()，值用 dynamic()，isGroup=True
  - 无 rowFields → 纯横向：列头用 groupRight()，值用 dynamic()，isGroup=False

JSON schema:
{
  "type": "horizontal_group",
  "reportName": "月度销售交叉表",
  "datasets": [{"dbCode":"sales","dbDynSql":"SELECT dept,month,amount FROM ..."}],
  "table": {
    "datasetCode": "sales",
    "title": "月度销售统计",
    "groupField": "month",              // 横向展开字段（groupRight）
    "rowFields": [                      // 纵向行头字段（可选，aggregate:"group"）
      {"field": "dept", "title": "部门"}
    ],
    "selectFields": [                   // 非分组维度字段（可选，aggregate:"select"，如姓名/性别）
      {"field": "name", "title": "姓名"}
    ],
    "valueFields": [                    // 值字段（dynamic）
      {"field": "amount", "title": "金额", "funcname": "SUM"}
    ],
    "statisticsRows": [                 // 可选：跟随分组扩展统计行（rightFollowExten）
      {"label": "合计:", "formula": "=SUM(G6)"},   // 第一行不带 follow
      {"label": "最高:", "formula": "=MAX(G6)"},   // 第二行起自动加 follow
      {"label": "平均:", "formula": "=AVERAGE(G6)"}
    ]
  }
}
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from jimureport_utils import (
    Session, parse_sql, save_db, make_designer, base_save,
    make_styles, print_summary, save_dataset,
)


def _col_letter(n: int) -> str:
    """1-based index → Excel column letter. 1→A, 2→B, ..., 26→Z."""
    return chr(ord("A") + n - 1)


def create_hgroup_report(session: Session, config: dict) -> str:
    report_name  = config["reportName"]
    table        = config["table"]
    ds_code      = table["datasetCode"]
    # groupRight() 括号内只能是裸字段名；若传入 dbCode.field（如 salesApi.month）则去掉前缀，
    # 否则引擎找不到字段 → 渲染报 "element cannot be mapped to a null key"
    group_field   = table["groupField"].split(".")[-1]
    row_fields    = table.get("rowFields", [])
    select_fields = table.get("selectFields", [])
    value_fields  = table.get("valueFields", [])
    stat_rows     = table.get("statisticsRows", [])
    is_hybrid     = bool(row_fields)
    n_static      = len(row_fields) + len(select_fields)
    n_group       = len(row_fields)
    n_select      = len(select_fields)
    n_values      = len(value_fields)

    # ── Step 1: 客户端预生成 report_id（orphan saveDb-friendly） ──────────────
    from jimureport_utils import gen_id
    report_id = gen_id()
    designer  = make_designer(report_id, report_name)

    # ── Step 2: save datasets（统一支持 JSON / SQL / API / requirement）──────────
    for ds in config.get("datasets", []):
        save_dataset(session, report_id, ds)

    # ── Step 3: build rows ───────────────────────────────────────────────────
    styles = make_styles()
    rows   = {"len": 200}
    merges = []

    S_TITLE, S_HEADER, S_DATA = 3, 2, 1
    row = 1

    # Title row — reserve extra cols for dynamic expansion
    title = table.get("title")
    if title:
        total_width = n_static + max(n_values * 12, 10)  # generous horizontal reserve
        rows[str(row)] = {"cells": {
            "1": {"text": title, "style": S_TITLE, "merge": [0, total_width - 1]}
        }, "height": 50}
        merges.append(f"B{row+1}:{_col_letter(total_width + 1)}{row+1}")
        row += 1

    if is_hybrid:
        # Hybrid mode ─────────────────────────────────────────────────────────
        # Header row: row-field + select-field headers (merge down 1) + groupRight column header
        header_cells = {}
        all_static = row_fields + select_fields
        for i, sf in enumerate(all_static):
            col_idx = i + 1
            header_cells[str(col_idx)] = {
                "text": sf["title"], "style": S_HEADER,
                "merge": [1, 0],   # merge down 1 row
            }
            merges.append(f"{_col_letter(col_idx + 1)}{row+1}:{_col_letter(col_idx + 1)}{row+2}")

        # groupRight header (horizontal expansion)
        gr_col = n_static + 1
        gr_cell = {
            "text": f"#{{{ds_code}.groupRight({group_field})}}",
            "style": S_HEADER,
            "aggregate": "group",
            "direction": "right",
        }
        if n_values > 1:
            gr_cell["merge"] = [0, n_values - 1]
            merges.append(f"{_col_letter(gr_col + 1)}{row+1}:{_col_letter(gr_col+n_values)}{row+1}")
        header_cells[str(gr_col)] = gr_cell
        rows[str(row)] = {"cells": header_cells, "height": 34}
        row += 1

        # Sub-header row: individual value field titles (under groupRight)
        sub_cells = {}
        for j, vf in enumerate(value_fields):
            sub_cells[str(gr_col + j)] = {"text": vf["title"], "style": S_HEADER}
        rows[str(row)] = {"cells": sub_cells, "height": 30}
        row += 1

        # Data row: group() for row fields + select for selectFields + dynamic() for value fields
        data_cells = {}
        for i, rf in enumerate(row_fields):
            data_cells[str(i+1)] = {
                "text": f"#{{{ds_code}.group({rf['field']})}}",
                "style": S_DATA, "aggregate": "group",
            }
        for i, sf in enumerate(select_fields):
            data_cells[str(n_group + i + 1)] = {
                "text": f"#{{{ds_code}.{sf['field']}}}",
                "style": S_DATA, "aggregate": "select", "subtotal": "-1",
            }
        for j, vf in enumerate(value_fields):
            cell = {"text": f"#{{{ds_code}.dynamic({vf['field']})}}", "style": S_DATA,
                    "aggregate": "dynamic", "subtotal": "-1", "funcname": "-1"}
            data_cells[str(gr_col + j)] = cell
        data_row = row
        rows[str(data_row)] = {"cells": data_cells}
        row += 1

        # Statistics rows (rightFollowExten)
        for k, sr in enumerate(stat_rows):
            stat_cells = {
                "1": {"text": sr["label"], "style": S_HEADER,
                      "merge": [0, n_static - 1] if n_static > 1 else [0, 0]},
            }
            # 第一条不设 rightFollowExten，从第二条起设
            formula_cell = {"text": sr["formula"], "style": S_HEADER}
            if k > 0:
                formula_cell["rightFollowExten"] = "follow"
            stat_cells[str(gr_col)] = formula_cell
            rows[str(row)] = {"cells": stat_cells}
            if n_static > 1:
                merges.append(f"B{row+1}:{_col_letter(n_static)}{row+1}")
            row += 1

        save_extra = {} if stat_rows else {
            "isGroup": True,
            "groupField": f"{ds_code}.{row_fields[0]['field']}",
        }

    else:
        # Pure horizontal mode ─────────────────────────────────────────────────
        # Header row: groupRight only
        gr_cell = {
            "text": f"#{{{ds_code}.groupRight({group_field})}}",
            "style": S_HEADER,
            "aggregate": "group",
            "direction": "right",
        }
        if n_values > 1:
            gr_cell["merge"] = [0, n_values - 1]
        rows[str(row)] = {"cells": {"1": gr_cell}, "height": 34}
        row += 1

        # Sub-header row for value fields
        if n_values > 1:
            sub_cells = {str(j+1): {"text": vf["title"], "style": S_HEADER}
                         for j, vf in enumerate(value_fields)}
            rows[str(row)] = {"cells": sub_cells, "height": 30}
            row += 1

        # Data row: dynamic() for each value field
        data_cells = {
            str(j+1): {"text": f"#{{{ds_code}.dynamic({vf['field']})}}", "style": S_DATA,
                       "subtotal": "-1", "funcname": "-1"}
            for j, vf in enumerate(value_fields)
        }
        rows[str(row)] = {"cells": data_cells}

        save_extra = {}

    # ── Step 4: save ─────────────────────────────────────────────────────────
    session.request("/save", base_save(
        report_id, designer,
        rows=rows, styles=styles, merges=merges,
        **save_extra,
    ))

    print_summary(report_id, report_name, session.base_url, "")
    return report_id
