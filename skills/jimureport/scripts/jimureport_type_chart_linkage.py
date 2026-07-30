"""
jimureport_type_chart_linkage.py — 图表联动报表（linkType=2）

支持三种联动：
  1. 表格→图表：点击单元格刷新当前报表内某个图表
  2. 图表→图表：点击柱/扇区刷新另一个图表
  3. 表格→图表 + 图表→图表 链式联动

核心约束（已在 create_report 中处理，无需 AI 关注）：
  - linkType 统一为 "2"
  - 触发单元格自动加 linkIds + display:"link"
  - 触发图表自动加 linkIds 到 extData
  - target.chartIndex 自动反查 layer_id

JSON schema:
{
  "type": "chart_linkage",
  "reportName": "...",
  "theme": "blue",
  "datasets": [
    {"dbCode":"catSum",   "dbDynSql":"...",  "isPage":"0"},
    {"dbCode":"brand",    "dbDynSql":"...where category='${category}'", "isPage":"0",
     "paramList":[{"paramName":"category","paramValue":"手机","searchFlag":0,"widgetType":"String","orderNum":1}]},
    {"dbCode":"month",    "dbDynSql":"...where brand='${brand}'",    "isPage":"0",
     "paramList":[{"paramName":"brand",   "paramValue":"苹果","searchFlag":0,"widgetType":"String","orderNum":1}]}
  ],
  "table":  {"datasetCode":"catSum", "title":"...", "columns":[...]},
  "charts": [
    {"datasetCode":"brand", "chartType":"bar.simple", "title":"按品牌"},
    {"datasetCode":"month", "chartType":"line.smooth","title":"按月度"}
  ],
  "linkages": [
    {
      "name": "按类别联动品牌图",
      "source": {"type":"cell","field":"category","dbCode":"catSum"},
      "target": {"chartIndex":0},
      "params": [{"paramName":"category","paramValue":"category","fieldName":"category","dbCode":"catSum"}]
    },
    {
      "name": "按品牌联动月度图",
      "source": {"type":"chart","chartIndex":0},
      "target": {"chartIndex":1},
      "params": [{"paramName":"brand","paramValue":"name","index":1}]
    }
  ]
}
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))


def create_chart_linkage_report(session, config: dict) -> str | None:
    import jimureport_creator
    cfg = {**config}
    # 默认布局：表格在上 + 多图表在下
    cfg.setdefault("layout", "multi_chart_below")
    return jimureport_creator.create_report(session, cfg)
