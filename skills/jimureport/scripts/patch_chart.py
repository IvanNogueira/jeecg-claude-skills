"""
通用图表配置 patch 工具
用法：python patch_chart.py --report-id <id> --token <token> [--base-url <url>] --config <json字符串或文件路径>

示例：
  python patch_chart.py --report-id 123 --token xxx --config '{"grid":{"bottom":100}}'
  python patch_chart.py --report-id 123 --token xxx --config ./my_changes.json
"""
import sys, json, argparse, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from jimureport_utils import Session, get_report, base_save

def deep_merge(base, patch):
    """递归合并 patch 到 base，list 直接替换"""
    for k, v in patch.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-id', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--base-url', default='http://localhost:8080/jmreport')
    parser.add_argument('--config', required=True, help='JSON字符串 或 .json文件路径')
    args = parser.parse_args()

    # 解析 --config 参数
    if os.path.isfile(args.config):
        with open(args.config, encoding='utf-8') as f:
            patch_cfg = json.load(f)
    else:
        patch_cfg = json.loads(args.config)

    session = Session(args.base_url, args.token)
    designer, design = get_report(session, args.report_id)

    for c in design.get('chartList', []):
        cfg = json.loads(c.get('config', '{}'))
        deep_merge(cfg, patch_cfg)
        c['config'] = json.dumps(cfg, ensure_ascii=False)

    resp = session.request('/save', base_save(args.report_id, designer, **design))
    print('OK' if resp.get('success') else f'FAIL: {resp}')

if __name__ == '__main__':
    main()