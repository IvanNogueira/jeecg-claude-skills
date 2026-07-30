import sys, os, json, mimetypes, argparse
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jimureport_utils import Session, gen_id, make_designer, make_styles, base_save

DEFAULT_BASE_URL = 'http://localhost:8080/jmreport'


def col_letter(idx):
    result = ''
    while idx > 0:
        idx, r = divmod(idx - 1, 26)
        result = chr(65 + r) + result
    return result


def upload_files(session, report_id, file_paths):
    for fpath in file_paths:
        fname = os.path.basename(fpath)
        ctype = mimetypes.guess_type(fname)[0] or 'application/octet-stream'
        with open(fpath, 'rb') as f:
            content = f.read()
        result = session.upload(
            '/source/datasource/files/add',
            files={'file': (fname, content, ctype)},
            params={'reportId': report_id, 'isSingle': 'true'}
        )
        if not result.get('success'):
            raise RuntimeError(f'Upload {fname} failed: {result.get("message")}')
        print(f'Uploaded {fname}')


def get_file_info(session, report_id):
    info = session.get(f'/source/datasource/files/get?reportId={report_id}')
    ds = info['result']
    return ds['id'], json.loads(ds['dbUrl'])


def build_sql(tables, join_field=None):
    if len(tables) == 1:
        return f'SELECT * FROM {tables[0]["name"]}'
    if not join_field:
        raise ValueError('多文件 JOIN 时必须指定 --join-on <字段名>')
    aliases = [chr(97 + i) for i in range(len(tables))]
    select_cols = [f'{aliases[0]}.*'] + [
        f'{alias}.*' for alias in aliases[1:]
    ]
    from_clause = f'{tables[0]["name"]} {aliases[0]}'
    joins = ' '.join(
        f'LEFT JOIN {t["name"]} {alias} ON {aliases[0]}.{join_field} = {alias}.{join_field}'
        for t, alias in zip(tables[1:], aliases[1:])
    )
    return f'SELECT {", ".join(select_cols)} FROM {from_clause} {joins}'


def parse_fields(session, sql, datasource_id):
    result = session.request('/queryFieldBySql', {'sql': sql, 'dbSource': datasource_id, 'type': '0'})
    fl_raw = result['result']['fieldList']
    return [
        {
            'fieldNamePhysics': f['fieldNamePhysics'],
            'fieldName': f['fieldName'],
            'fieldText': f.get('fieldText', f['fieldName']),
            'widgetType': f.get('widgetType', 'String'),
            'isShow': '1', 'isQuery': '0',
            'orderNum': i,
        }
        for i, f in enumerate(fl_raw)
    ]


def save_dataset(session, report_id, db_code, db_name, sql, datasource_id, field_list):
    payload = {
        'izSharedSource': 0,
        'jimuReportId': report_id,
        'dbCode': db_code,
        'dbChName': db_name,
        'dbType': '5',
        'dbSource': datasource_id,
        'isList': '1',
        'isPage': '1',
        'dbDynSql': sql,
        'jsonData': '', 'apiConvert': '', 'apiUrl': '', 'apiMethod': '0',
        'fieldList': field_list,
        'paramList': [],
    }
    r1 = session.request('/saveDb', payload)
    db_id = r1['result']['id']
    payload['id'] = db_id
    session.request('/saveDb', payload)
    print(f'Dataset saved: db_id={db_id}')
    return db_id


def build_and_save_report(session, report_id, report_name, db_code, field_list):
    styles = make_styles()
    styles.append({'align': 'center'})  # index 5: col0 no border
    n = len(field_list)
    end_col = col_letter(n + 1)
    rows = {
        '1': {
            'cells': {
                '0': {'text': '', 'style': 5},
                '1': {'text': report_name, 'style': 0, 'merge': [0, n - 1]},
            },
            'height': 45,
        },
        '2': {'cells': {'0': {'text': '', 'style': 5}}, 'height': 15},
        '3': {
            'cells': dict(
                [('0', {'text': '', 'style': 5})] +
                [(str(i + 1), {'text': f['fieldText'], 'style': 4}) for i, f in enumerate(field_list)]
            ),
            'height': 34,
        },
        '4': {
            'cells': dict(
                [('0', {'text': '', 'style': 5})] +
                [(str(i + 1), {'text': '#{' + db_code + '.' + f['fieldName'] + '}', 'style': 2})
                 for i, f in enumerate(field_list)]
            ),
        },
        'len': 200,
    }
    cols = dict(
        [('0', {'width': 30})] +
        [(str(i + 1), {'width': 100}) for i in range(n)] +
        [('len', 100)]
    )
    designer = make_designer(report_id, report_name)
    session.request('/save', base_save(
        report_id, designer,
        rows=rows, cols=cols, styles=styles, merges=[f'B1:{end_col}1'], chartList=[]
    ))


def main():
    parser = argparse.ArgumentParser(
        description='积木报表多文件数据集生成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  单文件:  python multi_file_report.py --token TOKEN --files 销售记录.xlsx --name "销售报表"
  多文件:  python multi_file_report.py --token TOKEN --files 销售.xlsx 产品.xlsx --name "销售产品联合报表" --join-on product_id
        '''
    )
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL, help=f'API 地址（默认 {DEFAULT_BASE_URL}）')
    parser.add_argument('--token', required=True, help='X-Access-Token')
    parser.add_argument('--files', nargs='+', required=True, help='Excel/CSV 文件路径（一个或多个）')
    parser.add_argument('--name', required=True, help='报表名称')
    parser.add_argument('--db-code', default='file_ds', help='数据集编码（默认 file_ds）')
    parser.add_argument('--join-on', default=None, help='多文件 JOIN 字段名（多文件时必填）')
    args = parser.parse_args()

    session = Session(args.base_url, args.token)
    report_id = gen_id()
    print(f'report_id={report_id}')

    upload_files(session, report_id, args.files)

    datasource_id, tables = get_file_info(session, report_id)
    print(f'datasource_id={datasource_id}')
    print(f'Tables: {[t["name"] for t in tables]}')

    sql = build_sql(tables, args.join_on)
    print(f'SQL={sql}')

    field_list = parse_fields(session, sql, datasource_id)
    print(f'Fields: {[f["fieldName"] for f in field_list]}')

    save_dataset(session, report_id, args.db_code, args.name, sql, datasource_id, field_list)
    build_and_save_report(session, report_id, args.name, args.db_code, field_list)

    host = args.base_url.replace('/jmreport', '')
    token = args.token
    print(f'report_id={report_id}')
    print(f'预览: {host}/jmreport/view/{report_id}?token={token}&tenantId=1')
    print(f'设计: {host}/jmreport/index/{report_id}?token={token}&tenantId=1')
    print('DONE')


if __name__ == '__main__':
    main()