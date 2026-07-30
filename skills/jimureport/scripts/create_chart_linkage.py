"""
create_chart_linkage.py
用途: 一次性完成「汇总表格 + 柱状图 + 饼图」三层图表联动报表的创建
流程: 创建3个YApi mock → 设置advmock → 创建报表 → 补丁linkIds
用法: python create_chart_linkage.py --token TOKEN [--name NAME]
"""
import sys, json, time, argparse, re
sys.stdout.reconfigure(encoding='utf-8')

# ── 路径 ─────────────────────────────────────────────────────────────────
import os; sys.path.insert(0, os.path.dirname(__file__))

from yapi_mock import init_yapi, create_mock, set_advmock
from jimureport_gen import chart_linkage
from jimureport_utils import Session, get_report, base_save

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--token',      required=True)
    p.add_argument('--base-url',   default=os.environ.get('JIMUREPORT_BASE_URL'), dest='base_url')
    p.add_argument('--yapi-email', default=os.environ.get('YAPI_EMAIL'), dest='yapi_email')
    p.add_argument('--yapi-pwd',   default=os.environ.get('YAPI_PASSWORD'), dest='yapi_pwd')
    p.add_argument('--name', default='奖学金统计联动报表')
    args = p.parse_args()

    if not args.base_url:
        p.error('--base-url 或环境变量 JIMUREPORT_BASE_URL 必须提供')
    if not args.yapi_email or not args.yapi_pwd:
        p.error('--yapi-email / --yapi-pwd 或环境变量 YAPI_EMAIL / YAPI_PASSWORD 必须提供')

    BASE_URL = args.base_url
    ts = int(time.time())
    TOKEN = args.token

    # ── Step 1: YApi mocks ──────────────────────────────────────────────
    print('>> 登录 YApi...')
    init_yapi(email=args.yapi_email, password=args.yapi_pwd)

    mock1_url = create_mock(path=f'/scholarship_summary_{ts}', title='奖学金类别汇总', data=[
        {'leibie': '初中', 'total': 47500},
        {'leibie': '高中', 'total': 74500},
        {'leibie': '大学', 'total': 111000}
    ])
    mock2_url = create_mock(path=f'/scholarship_by_school_{ts}', title='奖学金学校分布', data=[
        {'name': '北京实验中学', 'value': 14000, 'type': ''},
        {'name': '南京一中',     'value': 12000, 'type': ''},
        {'name': '广州育才中学', 'value': 9000,  'type': ''},
        {'name': '成都七中',     'value': 12500, 'type': ''}
    ])
    mock3_url = create_mock(path=f'/scholarship_by_region_{ts}', title='奖学金地区分布', data=[
        {'name': '华北', 'value': 8000, 'type': ''},
        {'name': '华东', 'value': 6000, 'type': ''}
    ])
    print(f'   mock1={mock1_url}')
    print(f'   mock2={mock2_url}')
    print(f'   mock3={mock3_url}')

    # ── Step 2: 获取接口ID ─────────────────────────────────────────────
    from yapi_mock import list_mocks
    ifaces = list_mocks()
    def find_id(part):
        for i in ifaces:
            if part in i.get('path',''):
                return str(i['_id'])
        raise ValueError(f'Interface not found: {part}')
    school_id = find_id(f'scholarship_by_school_{ts}')
    region_id = find_id(f'scholarship_by_region_{ts}')

    # ── Step 3: advmock 过滤脚本 ────────────────────────────────────────
    print('>> 设置 advmock...')
    set_advmock(iface_id=school_id, enable=True, script="""
var leibie = params.leibie || '初中';
var d = {
  '初中': [{name:'北京实验中学',value:14000,type:''},{name:'南京一中',value:12000,type:''},{name:'广州育才中学',value:9000,type:''},{name:'成都七中',value:12500,type:''}],
  '高中': [{name:'北京四中',value:22000,type:''},{name:'上海中学',value:20000,type:''},{name:'广雅中学',value:13000,type:''},{name:'重庆一中',value:19500,type:''}],
  '大学': [{name:'北京大学',value:38000,type:''},{name:'复旦大学',value:37000,type:''},{name:'中山大学',value:19000,type:''},{name:'四川大学',value:17000,type:''}]
};
mockJson = {data: d[leibie] || d['初中']};
""")
    set_advmock(iface_id=region_id, enable=True, script="""
var x = params.xuexiao || '北京实验中学';
var d = {
  '北京实验中学':[{name:'华北',value:8000,type:''},{name:'华东',value:6000,type:''}],
  '南京一中':[{name:'华东',value:7000,type:''},{name:'华南',value:5000,type:''}],
  '广州育才中学':[{name:'华南',value:9000,type:''}],
  '成都七中':[{name:'西南',value:8500,type:''},{name:'华北',value:4000,type:''}],
  '北京四中':[{name:'华北',value:12000,type:''},{name:'华东',value:10000,type:''}],
  '上海中学':[{name:'华东',value:11000,type:''},{name:'华南',value:9000,type:''}],
  '广雅中学':[{name:'华南',value:13000,type:''}],
  '重庆一中':[{name:'西南',value:11500,type:''},{name:'华北',value:8000,type:''}],
  '北京大学':[{name:'华北',value:20000,type:''},{name:'华东',value:18000,type:''}],
  '复旦大学':[{name:'华东',value:22000,type:''},{name:'西南',value:15000,type:''}],
  '中山大学':[{name:'华南',value:19000,type:''}],
  '四川大学':[{name:'西南',value:17000,type:''}]
};
mockJson = {data: d[x] || d['北京实验中学']};
""")

    # ── Step 4: 创建报表 ────────────────────────────────────────────────
    print('>> 创建报表...')
    proc = chart_linkage(
        token=TOKEN, name=args.name,
        datasets=[
            {'dbCode':'summary_ds','dbChName':'类别汇总','dbType':'1','apiUrl':mock1_url,
             'fieldList':[['leibie','类别'],['total','总奖学金']],'isPage':'0'},
            {'dbCode':'school_ds','dbChName':'学校分布','dbType':'1',
             'apiUrl':mock2_url+'?leibie=${leibie}',
             'paramList':[{'paramName':'leibie','paramValue':'初中','widgetType':'String','orderNum':0,'searchFlag':0}],
             'fieldList':[['name','学校名称'],['value','奖学金金额'],['type','类型']],'isPage':'0'},
            {'dbCode':'region_ds','dbChName':'地区分布','dbType':'1',
             'apiUrl':mock3_url+'?xuexiao=${xuexiao}',
             'paramList':[{'paramName':'xuexiao','paramValue':'北京实验中学','widgetType':'String','orderNum':0,'searchFlag':0}],
             'fieldList':[['name','地区'],['value','奖学金金额'],['type','类型']],'isPage':'0'}
        ],
        table={'datasetCode':'summary_ds','title':'奖学金类别汇总',
               'columns':[{'field':'leibie','title':'类别','width':150},{'field':'total','title':'总奖学金(元)','width':150}]},
        charts=[
            {'datasetCode':'school_ds','chartType':'bar.simple','title':'各学校奖学金（点击柱子→地区饼图）','width':'600','height':'350'},
            {'datasetCode':'region_ds','chartType':'pie.normal','title':'各地区奖学金分布','width':'600','height':'350'}
        ],
        linkages=[
            {'name':'表格类别→柱状图','sourceType':'cell','sourceDbCode':'summary_ds','sourceField':'leibie','targetChartIndex':0,'paramName':'leibie','paramValue':'leibie'},
            {'name':'柱状图→饼图','sourceType':'chart','sourceChartIndex':0,'targetChartIndex':1,'paramName':'xuexiao','paramValue':'name'}
        ]
    )
    stdout = proc.stdout if hasattr(proc,'stdout') else str(proc)
    m = re.search(r'report_id[=:\s]+(\S+)', stdout)
    if not m: raise RuntimeError('Cannot parse report_id from: '+stdout[:300])
    report_id = m.group(1)
    print(f'   report_id={report_id}')

    # ── Step 5: 补丁 linkIds ────────────────────────────────────────────
    print('>> 补丁联动...')
    session = Session(BASE_URL, TOKEN)
    layer_bar, layer_pie = None, None
    _, design = get_report(session, report_id)
    for c in design.get('chartList', []):
        ext = c.get('extData', {})
        if ext.get('dbCode') == 'school_ds': layer_bar = c.get('layer_id')
        if ext.get('dbCode') == 'region_ds': layer_pie = c.get('layer_id')

    r1 = session.request('/link/saveAndEdit', {
        'linkName':'表格类别→柱状图','linkType':'2','reportId':report_id,
        'linkChartId':layer_bar,'requirement':'',
        'parameter':json.dumps([{'paramName':'leibie','paramValue':'leibie','tableIndex':0,'dbCode':'summary_ds','fieldName':'leibie'}],ensure_ascii=False)
    })
    r2 = session.request('/link/saveAndEdit', {
        'linkName':'柱状图学校→饼图','linkType':'2','reportId':report_id,
        'linkChartId':layer_pie,'requirement':'',
        'parameter':json.dumps([{'paramName':'xuexiao','paramValue':'name','index':1}],ensure_ascii=False)
    })
    link1_id, link2_id = r1['result'], r2['result']

    _, design = get_report(session, report_id)
    design['rows']['3']['cells']['1']['linkIds'] = link1_id
    design['rows']['3']['cells']['1']['display'] = 'link'
    for c in design['chartList']:
        ext = c.get('extData', {})
        lid = c.get('layer_id','')
        ext['chartId'] = lid; ext['id'] = lid
        ext['dataType'] = 'api'
        if lid == layer_bar: ext['linkIds'] = link2_id
        c['extData'] = ext
    session.request('/save', base_save(report_id, _, **design))

    # ── 输出 ─────────────────────────────────────────────────────────────
    host = BASE_URL.replace('/jmreport','')
    print('\n' + '='*50)
    print(f'报表创建成功: {args.name}')
    print(f'  report_id: {report_id}')
    print(f'  预览: {host}/jmreport/view/{report_id}?token={TOKEN}&tenantId=1')
    print(f'  设计: {host}/jmreport/index/{report_id}?token={TOKEN}&tenantId=1')
    print('='*50)

if __name__ == '__main__':
    main()