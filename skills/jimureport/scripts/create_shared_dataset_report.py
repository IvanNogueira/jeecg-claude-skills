"""
create_shared_dataset_report.py
================================
创建「共享数据集」报表的完整脚本：
  1. 创建 YApi mock 接口（商品订单数据）
  2. 创建全局共享数据集（izSharedSource=1, jimuReportId=""）
  3. 用 api_dataset() 生成按订单日期分组的报表
  4. patch 报表数据集 → izSharedSource=1 + dbSource=共享数据集ID

用法：
  python create_shared_dataset_report.py --token TOKEN --base-url URL --yapi-email EMAIL --yapi-pwd PWD
  或设置环境变量 JIMUREPORT_BASE_URL / YAPI_EMAIL / YAPI_PASSWORD
"""
import sys, time, re, requests, argparse, os
sys.path.insert(0, r'C:\Users\Administrator\.claude\skills\jimureport\scripts')
sys.stdout.reconfigure(encoding='utf-8')

from yapi_mock          import init_yapi, create_mock
from jimureport_core    import Session
from jimureport_dataset import save_db
from jimureport_gen     import api_dataset

# ── 命令行参数 ────────────────────────────────────────────────────────
_p = argparse.ArgumentParser()
_p.add_argument('--token',      required=True)
_p.add_argument('--base-url',   default=os.environ.get('JIMUREPORT_BASE_URL'), dest='base_url')
_p.add_argument('--yapi-email', default=os.environ.get('YAPI_EMAIL'), dest='yapi_email')
_p.add_argument('--yapi-pwd',   default=os.environ.get('YAPI_PASSWORD'), dest='yapi_pwd')
_p.add_argument('--name',       default='共享数据集测试', dest='report_name')
_args = _p.parse_args()

if not _args.base_url:
    _p.error('--base-url 或环境变量 JIMUREPORT_BASE_URL 必须提供')
if not _args.yapi_email or not _args.yapi_pwd:
    _p.error('--yapi-email / --yapi-pwd 或环境变量 YAPI_EMAIL / YAPI_PASSWORD 必须提供')

BASE_URL      = _args.base_url
TOKEN         = _args.token
YAPI_EMAIL    = _args.yapi_email
YAPI_PASSWORD = _args.yapi_pwd
REPORT_NAME   = _args.report_name
SHARED_DBCODE = 'shared_goods_order'

# ── 商品订单测试数据 ─────────────────────────────────────────────────
MOCK_DATA = [
    {"order_date":"2024-01-15","order_no":"ORD2024001","goods_name":"苹果手机",   "category":"手机","quantity":2,"unit_price":5999.0, "total_amount":11998.0},
    {"order_date":"2024-01-15","order_no":"ORD2024002","goods_name":"华为笔记本", "category":"电脑","quantity":1,"unit_price":8999.0, "total_amount":8999.0},
    {"order_date":"2024-01-20","order_no":"ORD2024003","goods_name":"小米平板",   "category":"平板","quantity":3,"unit_price":2499.0, "total_amount":7497.0},
    {"order_date":"2024-01-20","order_no":"ORD2024004","goods_name":"索尼耳机",   "category":"配件","quantity":5,"unit_price":1299.0, "total_amount":6495.0},
    {"order_date":"2024-02-10","order_no":"ORD2024005","goods_name":"三星电视",   "category":"家电","quantity":1,"unit_price":12999.0,"total_amount":12999.0},
    {"order_date":"2024-02-10","order_no":"ORD2024006","goods_name":"苹果手机",   "category":"手机","quantity":2,"unit_price":5999.0, "total_amount":11998.0},
    {"order_date":"2024-02-15","order_no":"ORD2024007","goods_name":"联想台式机", "category":"电脑","quantity":2,"unit_price":6999.0, "total_amount":13998.0},
    {"order_date":"2024-02-15","order_no":"ORD2024008","goods_name":"小米手机",   "category":"手机","quantity":4,"unit_price":2999.0, "total_amount":11996.0},
    {"order_date":"2024-03-05","order_no":"ORD2024009","goods_name":"iPad",       "category":"平板","quantity":2,"unit_price":4599.0, "total_amount":9198.0},
    {"order_date":"2024-03-05","order_no":"ORD2024010","goods_name":"戴尔显示器", "category":"配件","quantity":3,"unit_price":1899.0, "total_amount":5697.0},
    {"order_date":"2024-03-10","order_no":"ORD2024011","goods_name":"华为手机",   "category":"手机","quantity":3,"unit_price":4499.0, "total_amount":13497.0},
    {"order_date":"2024-03-10","order_no":"ORD2024012","goods_name":"惠普打印机", "category":"配件","quantity":1,"unit_price":3299.0, "total_amount":3299.0},
]

FIELD_LIST = [
    ["order_date",   "订单日期"],
    ["order_no",     "订单编号"],
    ["goods_name",   "商品名称"],
    ["category",     "商品类别"],
    ["quantity",     "数量"],
    ["unit_price",   "单价(元)"],
    ["total_amount", "金额(元)"],
]

COLUMNS = [
    {"field":"order_date",   "title":"订单日期",  "width":120, "group":True, "subtotalText":"小计"},
    {"field":"order_no",     "title":"订单编号",  "width":140},
    {"field":"goods_name",   "title":"商品名称",  "width":150},
    {"field":"category",     "title":"商品类别",  "width":100},
    {"field":"quantity",     "title":"数量",      "width":80,  "funcname":"SUM"},
    {"field":"unit_price",   "title":"单价(元)",  "width":110},
    {"field":"total_amount", "title":"金额(元)",  "width":120, "funcname":"SUM"},
]

H = {'X-Access-Token': TOKEN, 'Content-Type': 'application/json'}


def main():
    # ── Step 1: 创建 YApi mock 接口 ────────────────────────────────
    print("=" * 55)
    print("Step 1: 创建 YApi mock 接口")
    init_yapi(email=YAPI_EMAIL, password=YAPI_PASSWORD)
    mock_path = f'/{SHARED_DBCODE}_{int(time.time())}'
    mock_url  = create_mock(mock_path, '商品订单共享数据集', MOCK_DATA)
    print(f"  mock_url: {mock_url}")

    # ── Step 2: 创建全局共享数据集 ────────────────────────────────
    print("\nStep 2: 创建全局共享数据集 (izSharedSource=1)")
    s = Session(BASE_URL, TOKEN)
    fl_dicts = [
        {"fieldName": f, "fieldText": t, "widgetType": "String",
         "orderNum": i, "tableIndex": 0, "extJson": "", "dictCode": ""}
        for i, (f, t) in enumerate(FIELD_LIST)
    ]
    shared_id = save_db(
        s, '', SHARED_DBCODE, '商品订单共享数据集',
        mock_url, fl_dicts,
        db_type='1', api_url=mock_url,
        is_list='1', is_page='0', is_shared=1,
    )
    print(f"  shared_dataset_id: {shared_id}")
    print(f"  dbCode: {SHARED_DBCODE}")

    # ── Step 3: 创建分组报表 ───────────────────────────────────────
    print("\nStep 3: 创建报表（按订单日期分组）")
    result  = api_dataset(
        token=TOKEN,
        name=REPORT_NAME,
        field_list=FIELD_LIST,
        columns=COLUMNS,
        api_url=mock_url,
        report_type='group',
    )
    stdout = result.stdout if hasattr(result, 'stdout') else str(result)

    # 解析 report_id 和 dataset_id
    rid_m = re.search(r'report_id[=:\s]+(\S+)', stdout)
    did_m = re.search(r'API数据集\s+OK\s+id=(\d+)', stdout)
    if not rid_m:
        print("ERROR: 无法解析 report_id\n", stdout[:300])
        return
    report_id  = rid_m.group(1)
    dataset_id = did_m.group(1) if did_m else None
    print(f"  report_id:  {report_id}")
    print(f"  dataset_id: {dataset_id}")

    # ── Step 4: patch 数据集 → 引用共享数据集 ────────────────────
    if dataset_id:
        print("\nStep 4: 关联报表数据集到共享数据集")
        r = requests.get(f'{BASE_URL}/loadDbData/{dataset_id}', headers=H, timeout=10)
        raw = r.json().get('result', {})
        db  = raw.get('reportDb', {})
        fl  = raw.get('fieldList', [])

        db['izSharedSource'] = 1          # 标记为共享引用
        db['dbSource']       = shared_id  # 指向全局共享数据集
        db['fieldList']      = fl
        db['paramList']      = []

        resp = requests.post(f'{BASE_URL}/saveDb', headers=H, json=db, timeout=10)
        ok   = resp.json().get('success')
        print(f"  patch {'OK' if ok else 'FAIL'}: izSharedSource=1, dbSource={shared_id}")
    else:
        print("\nStep 4: 跳过（未能解析 dataset_id）")

    # ── 输出结果 ──────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print(f"✓ 报表名称 : {REPORT_NAME}")
    print(f"✓ report_id: {report_id}")
    print(f"✓ 共享数据集 ID: {shared_id}  dbCode: {SHARED_DBCODE}")
    print(f"✓ Mock 接口: {mock_url}")
    print(f"\n预览地址  : {BASE_URL.replace('/jmreport','')}/jmreport/view/{report_id}?token={TOKEN}&tenantId=2")
    print(f"设计器地址: {BASE_URL.replace('/jmreport','')}/jmreport/index/{report_id}?token={TOKEN}&tenantId=2")


if __name__ == '__main__':
    main()
