"""
jimureport_report.py — 报表创建/读取/保存（make_designer / base_save / get_report）
"""
import json
from concurrent.futures import ThreadPoolExecutor

from jimureport_core import Session, gen_code, DEFAULT_BASE_URL, DEFAULT_TOKEN, DEFAULT_TENANT


def report_urls(report_id: str, base_url: str = DEFAULT_BASE_URL,
                token: str = DEFAULT_TOKEN, tenant: str = DEFAULT_TENANT) -> tuple[str, str]:
    """返回 (preview_url, design_url)。"""
    host = base_url.removesuffix("/jmreport").rstrip("/")
    qs   = f"token={token}&tenantId={tenant}"
    return (
        f"{host}/jmreport/view/{report_id}?{qs}",
        f"{host}/jmreport/index/{report_id}?{qs}",
    )


def make_designer(report_id: str, name: str, **extra) -> dict:
    return {
        "id":          report_id,
        "code":        gen_code(),
        "name":        name,
        "reportName":  name,
        "type":        "0",
        "template":    0,
        "delFlag":     0,
        "viewCount":   0,
        "updateCount": 0,
        "submitForm":  0,
        **extra,
    }


def base_save(report_id: str, designer_obj: dict, **overrides) -> dict:
    """
    构造 /jmreport/save 请求体。
    只有 designerObj 会被 json.dumps；其他字段保持原始 Python 对象。
    """
    payload: dict = {
        "designerObj":  json.dumps(designer_obj, ensure_ascii=False),
        "name":         "sheet1",
        "sheetId":      "default",
        "sheetName":    "默认Sheet",
        "sheetOrder":   "0",
        "freeze":       "A1",
        "freezeLineColor": "rgb(185, 185, 185)",
        "excel_config_id": report_id,
        "rows":         {"len": 200},
        "cols":         {"len": 100},
        "styles":       [],
        "merges":       [],
        "chartList":    [],
        "imgList":      [],
        "barcodeList":  [],
        "qrcodeList":   [],
        "loopBlockList":    [],
        "zonedEditionList": [],
        "fixedPrintHeadRows": [],
        "fixedPrintTailRows": [],
        "hiddenCells":    [],
        "submitHandlers": [],
        "validations":    [],
        "autofilter":     {},
        "dbexps":         [],
        "dicts":          [],
        "displayConfig":  {},
        "printConfig": {
            "paper": "A4", "width": 210, "height": 297, "definition": 1,
            "isBackend": False, "marginX": 10, "marginY": 10,
            "layout": "portrait", "printCallBackUrl": "",
        },
        "querySetting":      {"izOpenQueryBar": False, "izDefaultQuery": True},
        "queryFormSetting":  {"useQueryForm": False, "dbKey": "", "idField": ""},
        "rpbar": {"show": True, "pageSize": "", "btnList": []},
        "fillFormToolbar": {"show": True, "btnList": [
            "save", "subTable_add", "verify", "subTable_del", "print", "close",
            "first", "prev", "next", "paging", "total", "last",
            "exportPDF", "exportExcel", "exportWord",
        ]},
        "hidden": {"rows": [], "cols": [], "conditions": {"rows": {}, "cols": {}}},
        "fillFormInfo":   {"layout": {"direction": "horizontal", "width": 200, "height": 45}},
        "recordSubTableOrCollection": {"group": [], "record": [], "range": []},
        "area":             False,
        "background":       False,
        "pyGroupEngine":    False,
        "isViewContentHorizontalCenter": False,
        "fillFormStyle":    "default",
        "dataRectWidth":    700,
    }
    payload.update(overrides)
    return payload


def get_report(session: Session, report_id: str) -> tuple[dict, dict]:
    """
    获取报表设计，返回 (designer_obj, design)。
    design 可直接 **展开传给 base_save。
    """
    r = session.get(f"/get/{report_id}")
    result = r["result"]
    json_str = result.get("jsonStr", "{}")
    design = json.loads(json_str) if isinstance(json_str, str) else (json_str or {})
    designer_obj = {
        "id":          result["id"],
        "code":        result.get("code", ""),
        "name":        result.get("name", ""),
        "reportName":  result.get("name", ""),
        "type":        result.get("reportType", result.get("type", "0")),
        "template":    result.get("template", 0),
        "delFlag":     result.get("delFlag", 0),
        "viewCount":   result.get("viewCount", 0),
        "updateCount": result.get("updateCount", 0),
        "submitForm":  result.get("submitForm", 0),
        "cssStr":      result.get("cssStr", ""),
        "jsStr":       result.get("jsStr", ""),
    }
    return designer_obj, design


def parallel_init_and_parse(
    session: Session,
    report_id: str,
    designer_obj: dict,
    sql: str,
    db_source: str = "",
    **save_overrides,
) -> list[dict]:
    """⚠️ 已不推荐。保留供旧脚本兼容。新脚本请用 parse_and_save_dataset。"""
    from jimureport_dataset import parse_sql
    with ThreadPoolExecutor(max_workers=2) as ex:
        save_fut  = ex.submit(
            session.request, "/save",
            base_save(report_id, designer_obj, **save_overrides)
        )
        parse_fut = ex.submit(parse_sql, session, sql, db_source)
        save_fut.result()
        return parse_fut.result()


def print_summary(report_id: str, report_name: str,
                  base_url: str = DEFAULT_BASE_URL, token: str = DEFAULT_TOKEN):
    preview, design = report_urls(report_id, base_url, token)
    print(f"\n{'=' * 50}")
    print(f"报表创建成功: {report_name}")
    print(f"  report_id:  {report_id}")
    print(f"  预览地址:   {preview}")
    print(f"  设计器地址: {design}")
    print(f"{'=' * 50}")


# ── Layout helpers (moved from jimureport_creator.py) ─────────────────────────

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
    """
    rows: dict = {}
    merges: list = []
    columns = table_config.get("columns", [])
    ds_code  = table_config["datasetCode"]
    col_count = len(columns)
    row = start_row
    group_config: dict = {}

    def _col(idx: int) -> str:
        result, n = "", idx + 1
        while n:
            n, r = divmod(n - 1, 26)
            result = chr(65 + r) + result
        return result

    # 标题行
    title = table_config.get("title")
    if title:
        rows[str(row)] = {"cells": {"0": {"text": title, "style": title_style,
                                          "merge": [0, col_count], "height": 50}}, "height": 50}
        ui_row = row + 1
        merges.append(f"A{ui_row}:{_col(col_count)}{ui_row}")
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
            cell["text"]      = f"#{{{ds_code}.group({field})}}"
            cell["aggregate"] = "group"
            if "subtotalText" in col:
                cell["subtotal"]     = "groupField"
                cell["funcname"]     = "-1"
                cell["subtotalText"] = col["subtotalText"]
            if col.get("textOrders"):
                cell["textOrders"] = col["textOrders"]   # "华北|华南|华东"
            if not group_config:
                group_config = {"isGroup": True, "groupField": f"{ds_code}.{field}"}
        elif col.get("funcname"):
            cell["text"]     = f"#{{{ds_code}.{field}}}"
            cell["aggregate"] = col.get("aggregate", "select")
            cell["subtotal"] = "-1"
            cell["funcname"] = col["funcname"]
            if col.get("decimalPlaces"):
                cell["decimalPlaces"] = col["decimalPlaces"]
        else:
            cell["text"] = f"#{{{ds_code}.{field}}}"
        # 列级 widgetType/dictCode/format 等可选属性透传
        for k in ("widgetType", "dictCode", "decimalPlaces", "format",
                  "align", "valign", "color", "bgcolor", "barcode",
                  "qrcode", "showSign", "expression"):
            if k in col and k not in cell:
                cell[k] = col[k]
        data_cells[str(i + 1)] = cell

    rows[str(row)] = {"cells": data_cells}
    row += 1
    return rows, merges, row, group_config


# ── Cross-cutting helpers ──────────────────────────────────────────────────────

def apply_params(design: dict, params: list[dict]) -> None:
    """Open query bar when params are defined (params are already in dataset paramList)."""
    if not params:
        return
    design["querySetting"] = {"izOpenQueryBar": True, "izDefaultQuery": True}


def apply_drilling(session, report_id: str, drilling: list[dict]) -> None:
    """Create drill-through links for each drilling config entry."""
    import json as _json
    for d in drilling:
        param_list = [{"linkField": p["from"], "destParam": p["to"]}
                      for p in d.get("params", [])]
        session.request("/link/saveAndEdit", {
            "reportId":    report_id,
            "linkName":    d.get("name", f"钻取_{d['field']}"),
            "linkType":    "0",
            "ejectType":   d.get("ejectType", "0"),
            "apiUrl":      "",
            "apiMethod":   "",
            "requirement": "",
            "linkChartId": "",
            "parameter":   _json.dumps(param_list, ensure_ascii=False),
        })


def apply_linkage(session, report_id: str, linkage: dict | None) -> None:
    """Create chart linkage link."""
    import json as _json
    if not linkage:
        return
    session.request("/link/saveAndEdit", {
        "reportId":    report_id,
        "linkName":    linkage.get("name", "图表联动"),
        "linkType":    "2",
        "ejectType":   "0",
        "apiUrl":      "",
        "apiMethod":   "",
        "requirement": "",
        "linkChartId": linkage.get("targetChartDataset", ""),
        "parameter":   _json.dumps([{
            "linkField": linkage["triggerField"],
            "destParam": linkage["targetParam"],
        }], ensure_ascii=False),
    })
