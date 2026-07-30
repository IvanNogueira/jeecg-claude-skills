"""
积木报表快速生成器 — 所有 type 的 JSON 模板封装为函数，Claude 只需传参即可。

用法（在 PowerShell 内联调用）：
    import sys
    sys.path.insert(0, r'C:\\Users\\Administrator\\.claude\\skills\\jimureport\\scripts')
    from jimureport_gen import group
    group(token="xxx", name="销售分组", sql="SELECT ...", columns=[...])
"""

import json, os, sys, subprocess, tempfile

DEFAULT_BASE_URL = os.environ.get('JIMUREPORT_BASE_URL')
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_config(config: dict, token: str, base_url: str = DEFAULT_BASE_URL):
    skill_dir = os.path.join(tempfile.gettempdir(), "jimureport")
    os.makedirs(skill_dir, exist_ok=True)
    safe_name = config.get("reportName", "report").replace("/", "_").replace("\\", "_")
    config_path = os.path.join(skill_dir, f"{safe_name}_create.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    creator = os.path.join(SCRIPTS_DIR, "jimureport_creator.py")
    result = subprocess.run(
        [sys.executable, creator, "--api-base", base_url, "--token", token, "--config", config_path],
        capture_output=True, text=True, encoding="utf-8",
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result


# ── standard（默认表格 / 可带图表）─────────────────────────────────────────────
def standard(token, name, sql, columns, *,
             db_source="", db_code="ds1", layout="table_only",
             theme="blue", is_page="1", chart=None,
             base_url=DEFAULT_BASE_URL):
    """普通表格报表，可选底部/顶部图表。
    chart 示例：{"datasetCode":"dc","chartType":"bar.simple","title":"图表"}
    如需独立图表数据集，在 extra_datasets 里追加后自行合并 datasets。
    """
    config = {
        "action": "create", "type": "standard", "reportName": name, "theme": theme,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": is_page}],
        "layout": layout,
        "table": {"datasetCode": db_code, "title": name, "columns": columns},
    }
    if chart:
        config["chart"] = chart
    return run_config(config, token, base_url)


# ── group（纵向分组 / 小计 / 自定义排序）────────────────────────────────────────
def group(token, name, sql, columns, *,
          db_source="", db_code="ds1", base_url=DEFAULT_BASE_URL):
    """纵向分组报表。
    columns 分组列加 group=True；数值列加 funcname="SUM"；可选 subtotalText、textOrders。
    示例 column：{"field":"region","title":"区域","group":True,"subtotalText":"合计","textOrders":"华北|华南|华东"}
    """
    config = {
        "action": "create", "type": "group", "reportName": name,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": "0"}],
        "table": {"datasetCode": db_code, "title": name, "columns": columns},
    }
    return run_config(config, token, base_url)


# ── horizontal_group（交叉表 / 跟随统计行）──────────────────────────────────────
def horizontal_group(token, name, sql, *, group_field, row_fields, value_fields,
                     select_fields=None, statistics_rows=None,
                     db_source="", db_code="ds1", base_url=DEFAULT_BASE_URL):
    """横向交叉表。
    row_fields    → 纵向分组列列表，如 [{"field":"stuNo","title":"学号"}]
    select_fields → 非分组维度列（姓名/性别等），可省略
    value_fields  → 横向动态值列，如 [{"field":"score","title":"成绩"}]
    statistics_rows → 跟随统计行，如 [{"label":"最高分：","formula":"=MAX(G6)"}]
    """
    table = {
        "datasetCode": db_code, "title": name,
        "groupField": group_field,
        "rowFields": row_fields,
        "selectFields": select_fields or [],
        "valueFields": value_fields,
    }
    if statistics_rows:
        table["statisticsRows"] = statistics_rows
    config = {
        "action": "create", "type": "horizontal_group", "reportName": name,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": "0"}],
        "table": table,
    }
    return run_config(config, token, base_url)


# ── param_query（带查询条件）────────────────────────────────────────────────────
def param_query(token, name, sql, columns, param_list, *,
                db_source="", db_code="ds1", is_page="1",
                base_url=DEFAULT_BASE_URL):
    """带查询条的报表，SQL 须包含 FreeMarker <#if isNotEmpty(x)>...
    param_list 示例：
      [{"paramName":"username","paramTxt":"账号","paramValue":"",
        "widgetType":"String","orderNum":1,"searchFlag":1,"searchMode":1}]
    searchMode: 1=输入框 2=范围 3=多选 4=单选 5=模糊 6=下拉树 8=时间
    """
    config = {
        "action": "create", "type": "param_query", "reportName": name,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": is_page, "paramList": param_list}],
        "table": {"datasetCode": db_code, "title": name, "columns": columns},
    }
    return run_config(config, token, base_url)


# ── multilevel（多级表头）───────────────────────────────────────────────────────
def multilevel(token, name, sql, columns, header_groups, *,
               db_source="", db_code="ds1", is_page="1",
               base_url=DEFAULT_BASE_URL):
    """多级合并表头报表。
    header_groups 示例：[{"title":"基本信息","span":3},{"title":"季度业绩","span":4}]
    """
    config = {
        "action": "create", "type": "multilevel", "reportName": name,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": is_page}],
        "table": {"datasetCode": db_code, "title": name,
                  "headerGroups": header_groups, "columns": columns},
    }
    return run_config(config, token, base_url)


# ── mastersub（主子表）──────────────────────────────────────────────────────────
def mastersub(token, name, master_sql, sub_sql, master_columns, sub_columns, *,
              link_field="id", sub_param="orderId", db_source="",
              master_code="master_ds", sub_code="sub_ds",
              base_url=DEFAULT_BASE_URL):
    """主子表套打式报表。master_sql / sub_sql 通常含 ${orderId} 参数占位符。"""
    config = {
        "action": "create", "type": "mastersub", "reportName": name,
        "datasets": [
            {"dbCode": master_code, "dbChName": "主表", "dbDynSql": master_sql, "dbSource": db_source},
            {"dbCode": sub_code,    "dbChName": "子表", "dbDynSql": sub_sql,    "dbSource": db_source},
        ],
        "master": {"datasetCode": master_code, "title": name, "columns": master_columns},
        "sub": {"datasetCode": sub_code, "title": "明细", "columns": sub_columns,
                "linkField": link_field, "subParam": sub_param},
    }
    return run_config(config, token, base_url)


# ── loopblock（循环块）──────────────────────────────────────────────────────────
def loopblock(token, name, sql, columns, *, group_label,
              db_source="", db_code="emp", base_url=DEFAULT_BASE_URL):
    """循环块报表（每部门/每人一块）。group_label 为分组字段名。"""
    config = {
        "action": "create", "type": "loopblock", "reportName": name,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": "0"}],
        "loop": {"detailDataset": db_code, "groupLabel": group_label, "columns": columns},
    }
    return run_config(config, token, base_url)


# ── fillform（数据填报）─────────────────────────────────────────────────────────
def fillform(token, name, sql, columns, *, key_field="id", editable_fields=None,
             enable_add=True, enable_edit=True, enable_delete=False,
             db_source="", db_code="ds1", is_page="1",
             base_url=DEFAULT_BASE_URL):
    """数据填报报表。editable_fields 列表指定允许编辑的字段名。"""
    config = {
        "action": "create", "type": "fillform", "reportName": name,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": is_page}],
        "table": {"datasetCode": db_code, "title": name, "keyField": key_field,
                  "columns": columns, "editableFields": editable_fields or []},
        "fillFormConfig": {"enableAdd": enable_add, "enableEdit": enable_edit,
                           "enableDelete": enable_delete},
    }
    return run_config(config, token, base_url)


# ── multisource（多源横向拼接）──────────────────────────────────────────────────
def multisource(token, name, sections, *, base_url=DEFAULT_BASE_URL):
    """多源横向拼接报表。
    sections 列表，每项：{"dbCode":"x","dbChName":"名","sql":"SELECT...","db_source":"","title":"标题","columns":[...]}
    """
    datasets = [
        {"dbCode": s["dbCode"], "dbChName": s.get("dbChName", s["dbCode"]),
         "dbDynSql": s["sql"], "dbSource": s.get("db_source", ""), "isPage": "0"}
        for s in sections
    ]
    sec_cfgs = [
        {"datasetCode": s["dbCode"], "title": s.get("title", s["dbCode"]), "columns": s["columns"]}
        for s in sections
    ]
    config = {
        "action": "create", "type": "multisource", "reportName": name,
        "datasets": datasets, "sections": sec_cfgs,
    }
    return run_config(config, token, base_url)


# ── multisheet（多 Sheet）───────────────────────────────────────────────────────
def multisheet(token, name, sheets, *, base_url=DEFAULT_BASE_URL):
    """多 Sheet 报表。sheets 列表直接对应 SKILL.md multisheet type 的 sheets 字段。"""
    config = {"action": "create", "type": "multisheet", "reportName": name, "sheets": sheets}
    return run_config(config, token, base_url)


# ── drilling（报表/网络钻取）────────────────────────────────────────────────────
def drilling(token, name, sql, columns, drilling_list, *,
             layout="table_only", chart=None,
             db_source="", db_code="ds1", is_page="0",
             base_url=DEFAULT_BASE_URL):
    """钻取报表。drilling_list 参考 SKILL.md drilling type 模板的 drilling 字段。
    linkIds / display / extData.linkIds 由 creator 自动回填，不要手填。
    """
    config = {
        "action": "create", "type": "drilling", "reportName": name, "layout": layout,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
                      "dbSource": db_source, "isPage": is_page}],
        "table": {"datasetCode": db_code, "title": name, "columns": columns},
        "drilling": drilling_list,
    }
    if chart:
        config["chart"] = chart
    return run_config(config, token, base_url)


# ── chart_linkage（图表联动）────────────────────────────────────────────────────
def chart_linkage(token, name, datasets, table, charts, linkages, *,
                  base_url=DEFAULT_BASE_URL):
    """图表联动报表。datasets/table/charts/linkages 直接对应 SKILL.md chart_linkage 模板字段。"""
    config = {
        "action": "create", "type": "chart_linkage", "reportName": name,
        "datasets": datasets, "table": table, "charts": charts, "linkages": linkages,
    }
    return run_config(config, token, base_url)


# ── template_print（套打）───────────────────────────────────────────────────────
def template_print(token, name, sql, cells, bg_image, *,
                   param_list=None, paper="A4", layout="portrait",
                   db_source="", db_code="order",
                   base_url=DEFAULT_BASE_URL):
    """套打报表。bg_image 可传 localPath 或 url；cells 坐标 1-based。
    bg_image 示例：{"localPath":"C:/bg.jpg","width":950,"height":683,"cols":7,"rows":15}
    cells 示例：[{"row":3,"col":4,"field":"order_no"}]
    """
    ds = {"dbCode": db_code, "dbChName": name, "dbDynSql": sql,
          "dbSource": db_source, "isPage": "0", "isList": "0"}
    if param_list:
        ds["paramList"] = param_list
    config = {
        "action": "create", "type": "template_print", "reportName": name,
        "paper": paper, "layout": layout,
        "datasets": [ds], "bgImage": bg_image, "cells": cells,
    }
    return run_config(config, token, base_url)


# ── file_dataset（Excel/CSV 文件数据集）─────────────────────────────────────────
def file_dataset(token, name, file_path, columns=None, *,
                 db_ch_name=None, base_url=DEFAULT_BASE_URL):
    """文件数据集报表。columns 的 field 须用拼音（如"xing_ming"）；省略则用全部字段。"""
    config = {
        "action": "file_dataset", "reportName": name,
        "file": {"localPath": file_path, "dbChName": db_ch_name or name},
        "table": {"title": name},
    }
    if columns:
        config["table"]["columns"] = columns
    return run_config(config, token, base_url)


# ── json_dataset（静态 JSON 数据集）─────────────────────────────────────────────
def json_dataset(token, name, records, field_list, columns, *,
                 db_code="my_data", base_url=DEFAULT_BASE_URL):
    """静态 JSON 数据集报表。dbCode 必须是字符串（不能纯数字）。
    field_list 示例：[["name","姓名"],["age","年龄"]]
    """
    config = {
        "action": "create", "type": "standard", "reportName": name,
        "datasets": [{"dbCode": db_code, "dbChName": name, "dbType": "3",
                      "isList": "1", "isPage": "0",
                      "jsonData": records, "fieldList": field_list}],
        "table": {"datasetCode": db_code, "title": name, "columns": columns},
    }
    return run_config(config, token, base_url)


# ── api_dataset（API 数据集）─────────────────────────────────────────────────────
def api_dataset(token, name, field_list, columns, *,
                api_url=None, mock_data=None, mock_path=None,
                yapi_email=None, yapi_password=None,
                db_code="api_data", api_method="0",
                is_list="1", is_page="0", param_list=None,
                report_type="standard", base_url=DEFAULT_BASE_URL):
    """API 数据集报表。支持两种方式提供接口：

    方式一：直接传已有接口 URL
        api_dataset(token, name, field_list, columns, api_url="https://...")

    方式二：传入 mock_data，自动创建 YApi mock 接口再建报表
        api_dataset(token, name, field_list, columns,
                    mock_data=[{"field": "value"}, ...],
                    mock_path="/my_report_20260522",      # 路径末尾须含日期/序号防覆盖
                    yapi_email="xxx@xxx.com",             # 可省略，自动读凭证
                    yapi_password="xxx")

    field_list 简写格式：[["fieldName", "字段中文名"], ...]
    report_type 可改为 "group" / "horizontal_group" 等。
    """
    if api_url is None and mock_data is None:
        raise ValueError("api_url 和 mock_data 必须提供其中一个")

    if mock_data is not None:
        sys.path.insert(0, SCRIPTS_DIR)
        from yapi_mock import init_yapi, create_mock
        init_yapi(email=yapi_email, password=yapi_password)
        if mock_path is None:
            import time
            mock_path = f"/{db_code}_{int(time.time())}"
        api_url = create_mock(path=mock_path, title=name, data=mock_data)
        print(f"  Mock 接口已创建: {api_url}")

    ds = {"dbCode": db_code, "dbChName": name, "dbType": "1",
          "apiUrl": api_url, "apiMethod": api_method,
          "isList": is_list, "isPage": is_page, "fieldList": field_list}
    if param_list:
        ds["paramList"] = param_list
    config = {
        "action": "create", "type": report_type, "reportName": name,
        "datasets": [ds],
        "table": {"datasetCode": db_code, "title": name, "columns": columns},
    }
    return run_config(config, token, base_url)
