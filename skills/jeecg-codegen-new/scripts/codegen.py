#!/usr/bin/env python3
"""JeecgBoot 代码生成器 — Freemarker 驱动

用法（典型）：
    python codegen.py \
        --style default/one \
        --ctx ctx.json \
        --backend-root /path/to/jeecg-module-system/jeecg-system-biz \
        --frontend-root /path/to/jeecgboot-vue3 \
        --flyway-dir /path/to/flyway/sql/mysql

只做一件事：读 ctx.json → 渲染 Freemarker 模板 → 按文件类型分发到目标项目目录。
模板内容由 jeecg-boot 官方维护，本脚本不修改它们。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = SKILL_DIR / 'lib'
TEMPLATES_DIR = SKILL_DIR / 'templates'
SCRIPTS_DIR = SKILL_DIR / 'scripts'
CACHE_DIR = SCRIPTS_DIR / '.cache'

JAR_NAMES = ['freemarker-2.3.32.jar', 'fastjson2.jar']

# 与 jeecg 后台 CgformEnum 一致：每种 stylePath 官方支持的前端风格
# 不允许的组合直接拒绝，避免 AI 选了模板没覆盖的组合
STYLE_FRONTEND_SUPPORT = {
    'default/one':           {'vue3', 'vue3Native'},
    'default/tree':          {'vue3', 'vue3Native'},
    'default/onetomany':     set(),                 # 仅 vue2，新流程不用
    'tab/onetomany':         {'vue3'},
    'inner-table/onetomany': {'vue3'},
    'erp/onetomany':         {'vue3', 'vue3Native'},
}
VALID_STYLES = set(STYLE_FRONTEND_SUPPORT.keys())


def build_classpath() -> str:
    sep = ';' if os.name == 'nt' else ':'
    paths = [str(LIB_DIR / n) for n in JAR_NAMES]
    paths.append(str(CACHE_DIR))
    return sep.join(paths)


def _javac_release_flags() -> list:
    """探测 javac 版本，返回兼容 JDK 8 的编译参数。
    JDK 9+ 支持 --release 8（语义最严，会按 JDK 8 标准库做符号检查）。
    JDK 8 自身没有 --release，必须用 -source/-target。
    """
    try:
        out = subprocess.run(['javac', '-version'], capture_output=True, text=True, check=True)
        ver = (out.stdout + out.stderr).strip()  # JDK 8 把版本输出到 stderr
    except Exception:
        return ['-source', '8', '-target', '8']
    # ver 形如 "javac 1.8.0_461" 或 "javac 21.0.8"
    import re as _re
    m = _re.search(r'javac\s+(\d+)(?:\.(\d+))?', ver)
    if not m:
        return ['-source', '8', '-target', '8']
    major = int(m.group(1))
    if major == 1:  # 1.8 → JDK 8
        return ['-source', '8', '-target', '8']
    return ['--release', '8']


def ensure_compiled():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    src = SCRIPTS_DIR / 'FtlRunner.java'
    cls = CACHE_DIR / 'FtlRunner.class'
    if cls.exists() and cls.stat().st_mtime >= src.stat().st_mtime:
        return
    sep = ';' if os.name == 'nt' else ':'
    jar_cp = sep.join(str(LIB_DIR / n) for n in JAR_NAMES)
    cmd = ['javac', '-encoding', 'UTF-8', *_javac_release_flags(), '-cp', jar_cp, '-d', str(CACHE_DIR), str(src)]
    print('[codegen] compiling FtlRunner …', ' '.join(cmd))
    subprocess.run(cmd, check=True)


COLUMN_DEFAULTS = {
    # 字段默认值。AI 只需传 fieldName + 业务相关字段，其它自动兜底。
    'fieldDbName': '',          # 兜底由 camel->snake 推算
    'filedComment': '',         # 注意拼写：jeecg 模板里就是 'filed' 不是 'field'
    'fieldDbType': 'string',
    'fieldType': 'java.lang.String',
    'classType': 'text',
    'nullable': 'Y',
    'isShowList': 'Y',
    'isShow': 'Y',
    'isQuery': 'N',
    'queryMode': 'single',
    'sort': 'N',
    'readonly': 'N',
    # defaultVal 故意不兜底：模板用 `<#if defaultVal??>` 判断有无默认值，兜底成 '' 会让数字字段渲染出非法的 `defaultValue: ,`。
    'dictTable': '',
    'dictText': '',
    'dictField': '',
    'fieldValidType': '',
    'uploadnum': '1',
}

EXTEND_PARAMS_DEFAULTS = {
    'picker': '',
    'pidField': '',
    'hasChildren': '',
    'text': '',
    'store': '',
    # multi: 模板用 `${...multi?default('true')}`（字符串插值到 :multiple="X"）。
    # ?default 不对“已存在的空串”生效，故默认必须是有效字面量而非 ''，否则渲染出 :multiple=""。
    'multi': 'true',
    # popupMulti: 模板统一用 `${...popupMulti?c}`（布尔转换），必须是 bool 而非 ''，否则报 expected boolean。
    'popupMulti': False,
    'cgButtonList': [],     # 模板里做 ?filter ?seq_contains，必须是列表
    'enhanceJavaList': [],
}

TABLEVO_DEFAULTS = {
    'fieldRowNum': 1,
    'extendParams': None,  # 用 EXTEND_PARAMS_DEFAULTS 填
    'ftlDescription': '',
    'tableName': '',
    'entityName': '',
}


def _camel_to_snake(s: str) -> str:
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s).lower()


def _snake_to_camel(s: str) -> str:
    if '_' not in s:
        return s
    parts = s.split('_')
    return parts[0] + ''.join(p[:1].upper() + p[1:] for p in parts[1:])


# sel_depart / sel_user 在 jeecg 官方模板里读 extendParams.text/store，并用 ?default("…")
# 兜底——但 ?default 只对 undefined 生效，对空字符串不生效。我们 setdefault('text','')
# 之后 Freemarker 看到的就是空串而非 undefined，导致最终 @Dict(dicText="", dicCode="")。
# 解法：在 _enrich_column 里按 classType 把这两个字段填成有效值。
SEL_CLASS_TYPE_DEFAULTS = {
    'sel_depart': {'text': 'depart_name', 'store': 'id'},
    'sel_user':   {'text': 'realname',    'store': 'username'},
}


# 这些字段由后端自动维护，前端表单/子表表格里默认不显示（与 jeecg online 默认一致）。
SYSTEM_FIELD_NAMES = {'createBy', 'createTime', 'updateBy', 'updateTime', 'sysOrgCode'}


def _enrich_column(col: dict, primary_key: str | None = None) -> dict:
    out = dict(col)
    fn = out.get('fieldName', '')
    out.setdefault('fieldDbName', _camel_to_snake(fn))
    # 默认隐藏：系统字段 + 主键 在前端表单/子表表格里默认不显示。
    # ⚠️ 不写死——仅当用户【没有显式传 isShow】时才兜底为 N；用户显式给了 isShow 就完全尊重。
    # 所以有特殊需求要展示创建人/创建时间等系统字段时，在该列传 "isShow":"Y" 即可照常显示。
    if 'isShow' not in col and (fn in SYSTEM_FIELD_NAMES or (primary_key and fn == primary_key)):
        out['isShow'] = 'N'
    for k, v in COLUMN_DEFAULTS.items():
        out.setdefault(k, v)
    if not out.get('filedComment'):
        out['filedComment'] = fn
    ext = out.get('extendParams') or {}
    for k, v in EXTEND_PARAMS_DEFAULTS.items():
        ext.setdefault(k, v)
    # sel_depart / sel_user 的 text/store 必须有值，否则 @Dict 注解会渲染空串
    sel_defaults = SEL_CLASS_TYPE_DEFAULTS.get(out.get('classType'))
    if sel_defaults:
        for k, v in sel_defaults.items():
            if not ext.get(k):
                ext[k] = v
    out['extendParams'] = ext
    return out


def _enrich_tablevo(tv: dict, ctx: dict) -> dict:
    out = dict(tv) if tv else {}
    out.setdefault('entityName', ctx.get('entityName', ''))
    out.setdefault('tableName', ctx.get('tableName', ''))
    out.setdefault('ftlDescription', ctx.get('description', ctx.get('tableName', '')))
    out.setdefault('fieldRowNum', 1)
    ext = out.get('extendParams') or {}
    for k, v in EXTEND_PARAMS_DEFAULTS.items():
        ext.setdefault(k, v)
    out['extendParams'] = ext
    return out


def normalize_ctx(ctx: dict) -> dict:
    """补齐 Freemarker 模板需要、但 AI 不一定显式传入的派生字段。
    模板内大量出现 po.foo == "Y" 这种比较，缺字段会抛 InvalidReferenceException，
    所以这里给每个 column 都补齐 21 个字段。"""
    if 'entityPackage' in ctx and 'entityPackagePath' not in ctx:
        ctx['entityPackagePath'] = str(ctx['entityPackage']).replace('.', '/')
    if 'currentDate' not in ctx:
        ctx['currentDate'] = time.strftime('%Y%m%d')

    # 主表字段
    pk = ctx.get('primaryKeyField') or 'id'
    cols = ctx.get('originalColumns') or []
    # 若 originalColumns 里没有主键列，自动在首位注入，确保 Entity 模板能生成 @TableId
    if not any(c.get('fieldName') == pk for c in cols):
        cols = [{
            'fieldName': pk,
            'filedComment': '主键',
            'fieldDbName': pk,
            'fieldDbType': 'string',
            'fieldType': 'java.lang.String',
            'classType': 'text',
            'nullable': 'Y',
            'isShowList': 'N',
            'isShow': 'N',
            'isQuery': 'N',
        }] + cols
    cols = [_enrich_column(c, pk) for c in cols]
    ctx['originalColumns'] = cols
    # 前端 columns（formSchema / 列表 / 高级查询用）：排除主键。
    # 前端模板对主键的处理：columns 里没有 id 列时，自动补一个 show:false 的隐藏主键字段
    # （编辑回填 id 用，不在表单显示）；若 columns 含可见 id 列，反而会渲染成一个"主键"输入框。
    # 后端 Entity / Mapper 用的是含主键的 originalColumns，不受此影响。
    if 'columns' not in ctx:
        ctx['columns'] = [c for c in cols if c.get('fieldName') != pk]
    else:
        fe_cols = [_enrich_column(c, pk) for c in ctx['columns']]
        ctx['columns'] = [c for c in fe_cols if c.get('fieldName') != pk]

    # tableVo
    ctx['tableVo'] = _enrich_tablevo(ctx.get('tableVo') or {}, ctx)

    # primaryKeyField 兜底
    if 'primaryKeyField' not in ctx:
        for c in cols:
            if c.get('fieldName') == 'id':
                ctx['primaryKeyField'] = 'id'
                break
        else:
            ctx['primaryKeyField'] = 'id'

    # 子表
    subs = ctx.get('subTables') or []
    for sub in subs:
        sub_pk = sub.get('primaryKeyField') or 'id'
        sub_cols = sub.get('originalColumns') or []
        # 若子表 originalColumns 里没有主键列，自动在首位注入（与主表逻辑一致）
        if not any(c.get('fieldName') == sub_pk for c in sub_cols):
            sub_cols = [{
                'fieldName': sub_pk,
                'filedComment': '主键',
                'fieldDbName': sub_pk,
                'fieldDbType': 'string',
                'fieldType': 'java.lang.String',
                'classType': 'text',
                'nullable': 'Y',
                'isShowList': 'N',
                'isShow': 'N',
                'isQuery': 'N',
            }] + sub_cols
        # 子表 JVxeTable 同样按 col.isShow 决定显示；系统字段和子表主键默认隐藏，
        # 同样仅在用户未显式传 isShow 时兜底（详见 _enrich_column）。
        sub_cols = [_enrich_column(c, sub_pk) for c in sub_cols]
        sub['originalColumns'] = sub_cols
        # jeecg 模板里子表对象用了拼写 sub.colums (少一个 n)，补上
        sub['colums'] = sub_cols
        sub['columns'] = sub_cols
        sub.setdefault('foreignKeys', [])
        sub.setdefault('originalForeignKeys', [])
        # foreignKeys 用于生成 Java setter / 前端字段名（模板里 ?cap_first / ?uncap_first），
        # 必须是 camelCase；originalForeignKeys 是 snake_case 数据库列名（用于 SQL）。
        # 用户经常两者都填 snake_case，这里统一规范化。
        sub['foreignKeys'] = [_snake_to_camel(k) for k in sub['foreignKeys']]
        sub.setdefault('foreignRelationType', '0')
        sub.setdefault('ftlDescription', sub.get('tableName', ''))
        sub.setdefault('primaryKeyField', 'id')
    ctx['subTables'] = subs
    return ctx


def run_freemarker(style: str, ctx_path: Path, work_dir: Path) -> int:
    cp = build_classpath()
    cmd = ['java', '-cp', cp, 'FtlRunner', str(TEMPLATES_DIR), style, str(ctx_path), str(work_dir)]
    print('[codegen] running FtlRunner …')
    res = subprocess.run(cmd, check=False)
    return res.returncode


def collect_outputs(work_dir: Path) -> list[Path]:
    return [p for p in work_dir.rglob('*') if p.is_file()]


def categorize(rel: Path) -> str:
    """按相对路径判定文件归属：backend / frontend-vue3 / frontend-vue3Native / mobile-uniapp / mobile-uniapp3 / sql / unknown"""
    parts = rel.parts
    name = rel.name
    if name.endswith('.sql'):
        return 'sql'
    if 'vue3Native' in parts:
        return 'frontend-vue3Native'
    if 'vue3' in parts:
        return 'frontend-vue3'
    if 'uniapp3' in parts:
        return 'mobile-uniapp3'
    if 'uniapp' in parts:
        return 'mobile-uniapp'
    return 'backend'


def strip_template_prefix(rel: Path) -> Path:
    """去掉模板根下的 'java/' 那一层，只保留业务相关目录。"""
    parts = list(rel.parts)
    if parts and parts[0] == 'java':
        parts = parts[1:]
    return Path(*parts)


def split_at_segment(rel: Path, segment: str) -> tuple[Path, Path]:
    """把 rel 分成 (segment 之前, segment 之后)，segment 自身不在结果中。"""
    parts = list(rel.parts)
    if segment in parts:
        idx = parts.index(segment)
        return Path(*parts[:idx]), Path(*parts[idx + 1:]) if parts[idx + 1:] else Path()
    return rel, Path()


def normalize_dst_name(p: Path) -> Path:
    # jeecg 官方模板用 __ 作为 . 的占位符（避开文件系统/模板引擎对 . 的特殊解析）。
    # 落地时还原成 . ，否则前端 import "./Foo.data" 解析不到 Foo__data.ts。
    # ⚠️ 例外：.sql（Flyway 菜单脚本）的 __ 是 Flyway 版本名规范（V<version>__<desc>.sql）的
    # 分隔符，必须保留——官方命名即 V%s_%d__menu_insert_%s.sql。若误还原成 . 会破坏 Flyway 解析。
    if p.suffix == '.sql':
        return p
    return p.with_name(p.name.replace('__', '.')) if '__' in p.name else p


def entity_module_dir(ctx: dict) -> str:
    # 前端模块独立子目录名：entityName 首字母小写。FtlSysEmployee → ftlSysEmployee。
    # 与 jeecg 官方约定一致（参考 src/views/system/sysConfig/）。
    name = str(ctx.get('entityName', ''))
    return name[:1].lower() + name[1:] if name else ''


def dispatch(work_dir: Path, args, ctx: dict) -> list[tuple[Path, Path]]:
    """把 work_dir 下的产物分发到目标项目，返回 [(src, dst), ...] 列表。
    分发规则：
      backend                   -> {backend_root}/src/main/java/{bussiPackage}/{entityPackage}/...
      backend mapper xml        -> {backend_root}/src/main/java/{bussiPackage}/{entityPackage}/mapper/xml/...
      frontend-vue3             -> {frontend_root}/src/views/{entityPackagePath}/...
      frontend-vue3Native       -> {frontend_root}/src/views/{entityPackagePath}/...（与 vue3 共享，由用户在 ctx 选风格）
      mobile-uniapp(3)          -> {mobile_root}/{entityPackagePath}/...（用户没传则跳过）
      sql                       -> {flyway_dir}/{filename}（菜单 SQL 多份重复，仅保留一份）
    """
    results: list[tuple[Path, Path]] = []
    sql_seen: set[str] = set()
    bussi_path = str(ctx.get('bussiPackage', '')).replace('.', '/')
    entity_pkg = ctx.get('entityPackage', '')
    entity_path = str(entity_pkg).replace('.', '/')
    module_dir = entity_module_dir(ctx)

    for src in collect_outputs(work_dir):
        rel = src.relative_to(work_dir)
        rel = strip_template_prefix(rel)
        cat = categorize(rel)

        if cat == 'sql':
            if not args.flyway_dir:
                continue
            if src.name in sql_seen:
                continue
            sql_seen.add(src.name)
            dst = Path(args.flyway_dir) / src.name
        elif cat == 'backend':
            if not args.backend_root:
                continue
            # rel 形如 org/jeecg/modules/biz/entity/Foo.java
            dst = Path(args.backend_root) / 'src/main/java' / rel
        elif cat in ('frontend-vue3', 'frontend-vue3Native'):
            if not args.frontend_root:
                continue
            wanted = 'vue3Native' if args.frontend_style == 'vue3Native' else 'vue3'
            if cat != f'frontend-{wanted}':
                continue  # 用户只要一种风格
            _, after = split_at_segment(rel, wanted)
            # 每个模块单独一层目录（jeecg 官方约定）：src/views/{entityPackage}/{entityNameLower}/...
            dst = Path(args.frontend_root) / 'src/views' / entity_path / module_dir / after
        elif cat == 'mobile-uniapp':
            if not args.mobile_root:
                continue
            _, after = split_at_segment(rel, 'uniapp')
            dst = Path(args.mobile_root) / entity_path / after
        elif cat == 'mobile-uniapp3':
            if not args.mobile_root:
                continue
            _, after = split_at_segment(rel, 'uniapp3')
            dst = Path(args.mobile_root) / entity_path / after
        else:
            continue
        results.append((src, normalize_dst_name(dst)))
    return results


def write_files(plan: list[tuple[Path, Path]], dry_run: bool, sql_rewrite: tuple[str, str] | None = None):
    for src, dst in plan:
        action = 'WOULD WRITE' if dry_run else 'WROTE'
        print(f'[codegen] {action} {dst}')
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.suffix == '.sql' and sql_rewrite:
            # 菜单 SQL 的 component 字段需要补上模块子目录；模板写的是 'system/FooList'，
            # 实际落地路径已变成 'system/foo/FooList'，不改前端会按旧路径加载组件 404。
            old, new = sql_rewrite
            content = src.read_text(encoding='utf-8')
            dst.write_text(content.replace(old, new), encoding='utf-8')
        else:
            shutil.copyfile(src, dst)


def parse_args():
    p = argparse.ArgumentParser(description='JeecgBoot codegen via Freemarker.')
    p.add_argument('--style', required=True, choices=sorted(VALID_STYLES))
    p.add_argument('--ctx', required=True, help='ctx.json 路径，含 bussiPackage / entityPackage / entityName / tableName / columns / subTables ...')
    p.add_argument('--backend-root', help='后端模块根，如 .../jeecg-module-system/jeecg-system-biz')
    p.add_argument('--frontend-root', help='前端项目根，如 .../jeecgboot-vue3')
    p.add_argument('--frontend-style', default='vue3', choices=['vue3', 'vue3Native'])
    p.add_argument('--mobile-root', help='移动端项目根（uniapp3），不需要可省略')
    p.add_argument('--flyway-dir', help='Flyway SQL 目录，菜单 SQL 会落到这里')
    p.add_argument('--out', help='[调试] 仅渲染到指定目录，不分发')
    p.add_argument('--dry-run', action='store_true', help='只打印目标路径，不实际写入')
    return p.parse_args()


def validate_style(style: str, frontend_style: str):
    supported = STYLE_FRONTEND_SUPPORT.get(style, set())
    if frontend_style not in supported:
        sys.exit(
            f'[codegen] 模板 {style} 不支持 {frontend_style}。\n'
            f'           可用前端风格: {sorted(supported) or "（仅后端，无前端模板）"}\n'
            f'           请改用其他 --style 或 --frontend-style 组合。'
        )


def main():
    args = parse_args()
    if not args.out:
        validate_style(args.style, args.frontend_style)
    ctx_path = Path(args.ctx).resolve()
    if not ctx_path.is_file():
        sys.exit(f'ctx file not found: {ctx_path}')

    with ctx_path.open(encoding='utf-8') as f:
        ctx = json.load(f)
    ctx = normalize_ctx(ctx)
    # 把规范化后的 ctx 落回临时文件，给 Java 用
    norm_path = ctx_path.with_suffix('.normalized.json')
    with norm_path.open('w', encoding='utf-8') as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)

    ensure_compiled()

    if args.out:
        work_dir = Path(args.out).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)
        rc = run_freemarker(args.style, norm_path, work_dir)
        if rc != 0:
            sys.exit(rc)
        print(f'[codegen] rendered to {work_dir}, skipping dispatch (--out 模式)')
        return

    with tempfile.TemporaryDirectory(prefix='jeecg-codegen-') as tmp:
        work_dir = Path(tmp)
        rc = run_freemarker(args.style, norm_path, work_dir)
        if rc != 0:
            sys.exit(rc)
        plan = dispatch(work_dir, args, ctx)
        entity_path = str(ctx.get('entityPackage', '')).replace('.', '/')
        module_dir = entity_module_dir(ctx)
        entity_name = ctx.get('entityName', '')
        sql_rewrite = (
            f"'{entity_path}/{entity_name}",
            f"'{entity_path}/{module_dir}/{entity_name}",
        ) if module_dir and entity_path and entity_name else None
        write_files(plan, args.dry_run, sql_rewrite)
        print(f'[codegen] {len(plan)} files dispatched.')


if __name__ == '__main__':
    main()
