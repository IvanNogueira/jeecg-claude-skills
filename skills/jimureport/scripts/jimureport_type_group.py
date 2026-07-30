"""
jimureport_type_group.py — 纵向分组报表（含小计 / 合计 / 自定义排序）

JSON schema:
{
  "type": "group",
  "reportName": "...",
  "datasets": [{"dbCode":"...", "dbDynSql":"..."}],
  "table": {
    "datasetCode": "...",
    "title": "...",
    "columns": [
      // 分组列：group:true → aggregate:"group"，可加 subtotalText 显示小计，textOrders 自定义排序
      {"field": "region", "title": "区域", "group": true,
       "subtotalText": "小计",
       "textOrders": "华北|华南|华东"},   // 可选：竖线分隔的显示顺序

      // 数值列：funcname=SUM/AVERAGE/MAX/MIN/COUNT，可加 decimalPlaces 保留小数
      {"field": "amount", "title": "金额", "funcname": "SUM", "decimalPlaces": 2}
    ]
  }
}

📌 注意（已在 build_table_rows 中处理）：
  - 分组列有 subtotalText 时，数值列必须有 funcname（否则小计/合计行数值空白）
  - textOrders 是单元格级属性，只挂在分组列；顺序按 | 分隔
  - 列级 widgetType / dictCode / decimalPlaces / format 等会自动透传
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))


def create_group_report(session, config: dict) -> str | None:
    import jimureport_creator
    cfg = {**config, "layout": config.get("layout", "table_only")}
    return jimureport_creator.create_report(session, cfg)
