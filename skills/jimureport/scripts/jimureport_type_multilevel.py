"""
jimureport_type_multilevel.py — 多级表头报表（支持 2 级表头分组）

支持场景：
  - 基础（multi-level-header-basic）：1 层 headerGroups + 列标题
  - 进阶（multi-level-header-advanced）：含合计行的 2 层表头（合计行用 customRows 覆盖）
  - API 数据集（multi-level-header-api）：dataset[].dbType="1" + apiUrl 即可

3 级以上嵌套表头：传 customRows / customMerges 跳过自动构建。
跨年度横向展开 + 多列纵向行头：用 type=horizontal_group（含 selectFields）。

JSON schema:
{
  "type": "multilevel",
  "reportName": "员工数据统计",
  "datasets": [{"dbCode":"emp","dbDynSql":"SELECT ..."}],   // 或 API/JSON
  "table": {
    "datasetCode": "emp",
    "title": "员工数据",
    "headerGroups": [
      {"title": "基本信息", "span": 3},
      {"title": "销售数据", "span": 4}
    ],
    "columns": [
      {"field":"name","title":"姓名"},{"field":"age","title":"年龄"},
      {"field":"dept","title":"部门"},
      {"field":"q1","title":"Q1"},{"field":"q2","title":"Q2"},
      {"field":"q3","title":"Q3"},{"field":"q4","title":"Q4"}
    ]
  }
}
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from jimureport_utils import (
    Session, parse_sql, save_db, make_designer, base_save,
    make_styles, print_summary, build_cols, save_dataset,
)


def _col_letter(n: int) -> str:
    """1-based column index → Excel column letter."""
    return chr(ord("A") + n - 1)


def create_multilevel_report(session: Session, config: dict) -> str:
    report_name   = config["reportName"]
    table         = config["table"]
    ds_code       = table["datasetCode"]
    columns       = table["columns"]
    header_groups = table.get("headerGroups", [])
    n_cols        = len(columns)

    # ── Step 1: create empty report ──────────────────────────────────────────
    r = session.request("/save", base_save("", make_designer("", report_name)))
    report_id = r["result"]["id"]
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

    # Title row
    title = table.get("title")
    if title:
        rows[str(row)] = {"cells": {
            "0": {"text": title, "style": S_TITLE, "merge": [0, n_cols]}
        }, "height": 50}
        merges.append(f"A{row+1}:{_col_letter(n_cols+1)}{row+1}")
        row += 1

    # First header row: group spans (horizontal merges only)
    if header_groups:
        first_header = {}
        col_cursor   = 1  # 1-based column index
        for grp in header_groups:
            span = grp["span"]
            cell = {"text": grp["title"], "style": S_HEADER}
            if span > 1:
                cell["merge"] = [0, span - 1]
                start = _col_letter(col_cursor + 1)   # +1 because col_cursor 1-based, A=col0
                end   = _col_letter(col_cursor + span) # exclusive end
                merges.append(f"{start}{row+1}:{end}{row+1}")
            first_header[str(col_cursor)] = cell
            col_cursor += span
        rows[str(row)] = {"cells": first_header, "height": 34}
        row += 1

    # Second header row: individual column titles
    rows[str(row)] = {"cells": {
        str(i+1): {"text": col["title"], "style": S_HEADER}
        for i, col in enumerate(columns)
    }, "height": 34}
    row += 1

    # Data row
    rows[str(row)] = {"cells": {
        str(i+1): {"text": f"#{{{ds_code}.{col['field']}}}", "style": S_DATA}
        for i, col in enumerate(columns)
    }}

    # ── Step 4: save ─────────────────────────────────────────────────────────
    cols = build_cols(columns)
    session.request("/save", base_save(
        report_id, designer,
        rows=rows, cols=cols, styles=styles, merges=merges,
    ))

    print_summary(report_id, report_name, session.base_url, "")
    return report_id
