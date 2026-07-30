"""
jimureport_type_drilling.py — 报表钻取（linkType=0/1）

支持三种钻取：
  - linkType=0  报表钻取报表（跳转到 targetReportId 对应的明细子报表）
  - linkType=1  报表钻取网络（跳转到 targetUrl 外部链接）
  - 图表钻取（source.type="chart"，linkType=0/1 均可）

核心约束（已在 create_report 中处理）：
  - 单元格自动加 linkIds + display:"link"
  - 图表自动加 linkIds 到 extData
  - linkType=0 reportId 用 targetReportId，linkType=1 reportId 用当前报表

JSON schema:
{
  "type": "drilling",
  "reportName": "销售汇总报表",
  "theme": "blue",
  "datasets": [{"dbCode":"sales","dbDynSql":"select category as name,sum(...) as value,'' as type from ... group by category","isPage":"0"}],
  "layout": "chart_bottom",
  "table": {"datasetCode":"sales","columns":[
    {"field":"name","title":"商品类别"},
    {"field":"value","title":"销售总额"}
  ]},
  "chart": {"datasetCode":"sales","chartType":"bar.simple","title":"各类别销售总额"},
  "drilling": [
    {
      "name": "报表钻取报表",
      "linkType": "0",
      "source": {"type":"cell","field":"name"},
      "targetReportId": "<明细子报表ID>",
      "params": [{"paramName":"category","paramValue":"name","fieldName":"category","dbCode":"sales"}]
    },
    {
      "name": "图表钻取报表",
      "linkType": "0",
      "source": {"type":"chart","chartIndex":0},
      "targetReportId": "<明细子报表ID>",
      "params": [{"paramName":"category","paramValue":"name","fieldName":""}]
    },
    {
      "name": "网络钻取",
      "linkType": "1",
      "source": {"type":"cell","field":"name"},
      "targetUrl": "https://www.baidu.com/s",
      "params": [{"paramName":"wd","paramValue":"name","fieldName":"name","dbCode":"sales"}]
    }
  ]
}

> 用户需要钻取目标明细子报表时，先用 type=param_query 或 type=standard
> 创建明细子报表（SQL 含 `<#if isNotEmpty(category)>and category='${category}'</#if>`），
> 拿到 ID 后传给 targetReportId。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))


def create_drilling_report(session, config: dict) -> str | None:
    import jimureport_creator
    return jimureport_creator.create_report(session, config)
