#!/usr/bin/env python3
"""
门户组件配置修改脚本

用法:
  python3 modify_component.py --api-base URL --token TOKEN --portal-id ID --component JSchedule --props '{"tabType":0,"singleRange":"week"}'

也可作为模块导入:
  from modify_component import modify_component, get_design_json, save_design_json
"""

import json
import urllib.request
import argparse
import sys
import tempfile
import os


def api_get(api_base, token, path):
    req = urllib.request.Request(f"{api_base}{path}")
    req.add_header("X-Access-Token", token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post(api_base, token, path, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{api_base}{path}", data=data, method="POST")
    req.add_header("X-Access-Token", token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_design_json(api_base, token, portal_id):
    """获取门户的 designJson（已解析为 dict）"""
    r = api_get(api_base, token, f"/eoa/portalapp/portalDesign/queryById?id={portal_id}")
    if not r.get("success"):
        raise RuntimeError(f"查询失败: {r.get('message')}")
    return json.loads(r["result"]["designJson"])


def save_design_json(api_base, token, portal_id, design):
    """保存 designJson 到门户"""
    r = api_post(api_base, token, "/eoa/portalapp/portalDesign/edit", {
        "id": portal_id,
        "designJson": json.dumps(design, ensure_ascii=False),
    })
    if not r.get("success"):
        raise RuntimeError(f"保存失败: {r.get('message')}")
    return r


# 需要双端同步的属性映射
SYNC_PROPS = {
    "JAppEnter": ["tabType", "noTabsData", "tabsData"],
    "JCmsNews": ["tabType", "noTabsData", "tabsData"],
    "JKnowledge": ["tabType", "noTabsData", "tabsData"],
    "JAppCarousel": ["list"],
    "JMyFlow": ["category", "order"],
    "JCollaPending": ["category", "order"],
    "JSystemNotice": ["msgCategory", "noticeType"],
}


def find_component(design, component=None, name=None):
    """在 webComponentData 中按 component 或 name 查找，返回 (index, comp)"""
    for i, c in enumerate(design.get("webComponentData", [])):
        if component and c.get("component") == component:
            return i, c
        if name and c.get("name") == name:
            return i, c
    return -1, None


def modify_component(api_base, token, portal_id, component=None, name=None, props=None, layout=None):
    """
    修改门户组件配置

    Args:
        component: 组件类型（如 JSchedule）
        name: 组件名称（如 "我的计划"），与 component 二选一
        props: 要修改的 defaultProps（dict）
        layout: 要修改的布局属性（dict，如 {"w": 12, "h": 6}）

    Returns:
        修改后的组件信息
    """
    design = get_design_json(api_base, token, portal_id)

    idx, web_comp = find_component(design, component, name)
    if idx < 0:
        target = component or name
        available = [f"{c['component']}({c['name']})" for c in design.get("webComponentData", [])]
        raise ValueError(f"未找到组件 '{target}'，可用组件: {', '.join(available)}")

    comp_type = web_comp["component"]
    comp_i = web_comp["i"]

    # 修改 Web 端 defaultProps
    if props:
        web_comp["defaultProps"].update(props)

    # 修改 Web 端布局
    if layout:
        for k, v in layout.items():
            if k in ("x", "y", "w", "h"):
                web_comp[k] = v

    # 同步 App 端
    sync_keys = SYNC_PROPS.get(comp_type, [])
    changed_sync_keys = [k for k in sync_keys if props and k in props]

    for app_comp in design.get("appComponentData", []):
        if app_comp.get("i") == comp_i:
            if props:
                # 同步需要同步的属性
                for k in changed_sync_keys:
                    app_comp["defaultProps"][k] = props[k]
                # 非同步属性也更新到 App 端（通用属性）
                for k in props:
                    if k not in sync_keys:
                        app_comp["defaultProps"][k] = props[k]
            break

    save_design_json(api_base, token, portal_id, design)

    return {
        "component": comp_type,
        "name": web_comp["name"],
        "i": comp_i,
        "synced_keys": changed_sync_keys,
    }


def remove_component(api_base, token, portal_id, component=None, name=None):
    """从门户中删除组件（Web + App 双端）"""
    design = get_design_json(api_base, token, portal_id)

    idx, web_comp = find_component(design, component, name)
    if idx < 0:
        raise ValueError(f"未找到组件 '{component or name}'")

    comp_i = web_comp["i"]
    comp_name = web_comp["name"]

    design["webComponentData"] = [c for c in design["webComponentData"] if c["i"] != comp_i]
    design["appComponentData"] = [c for c in design["appComponentData"] if c["i"] != comp_i]

    save_design_json(api_base, token, portal_id, design)
    return {"removed": comp_name, "i": comp_i}


def list_components(api_base, token, portal_id):
    """列出门户中的所有组件"""
    design = get_design_json(api_base, token, portal_id)
    result = []
    for c in design.get("webComponentData", []):
        result.append({
            "component": c["component"],
            "name": c["name"],
            "i": c["i"],
            "x": c["x"], "y": c["y"], "w": c["w"], "h": c["h"],
        })
    return result


def list_portals(api_base, token):
    """列出所有门户"""
    r = api_get(api_base, token, "/eoa/portalapp/portalDesign/list?bizMode=portal&pageNo=1&pageSize=50")
    return r.get("result", {}).get("records", [])


def change_portal_type(api_base, token, portal_id, new_type):
    """
    修改门户类型，自动处理唯一性冲突。
    对于 personal/system/template 类型，如果已存在，自动将旧的改为 common。
    """
    # 唯一类型需要先处理冲突
    if new_type in ("personal", "system", "template"):
        check = api_get(api_base, token,
                        f"/eoa/portalapp/portalDesign/duplicateTypeCheck?portalCategory={new_type}")
        if not check.get("success"):
            # 找到现有的同类型门户并改为 common
            portals = list_portals(api_base, token)
            for p in portals:
                if p.get("portalCategory") == new_type and p["id"] != portal_id:
                    api_post(api_base, token, "/eoa/portalapp/portalDesign/edit",
                             {"id": p["id"], "portalCategory": "common"})
                    print(f"已将 \"{p['name']}\" 从 {new_type} 改为 common")
                    break

    # 修改目标门户类型
    r = api_post(api_base, token, "/eoa/portalapp/portalDesign/edit",
                 {"id": portal_id, "portalCategory": new_type})
    if not r.get("success"):
        raise RuntimeError(f"修改失败: {r.get('message')}")
    return {"id": portal_id, "portalCategory": new_type}


def main():
    parser = argparse.ArgumentParser(description="门户组件配置修改")
    parser.add_argument("--api-base", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--portal-id", required=True)

    sub = parser.add_subparsers(dest="action", help="操作类型")

    # modify
    p_mod = sub.add_parser("modify", help="修改组件配置")
    p_mod.add_argument("--component", help="组件类型")
    p_mod.add_argument("--name", help="组件名称")
    p_mod.add_argument("--props", help="JSON格式的属性")
    p_mod.add_argument("--layout", help="JSON格式的布局属性")

    # remove
    p_rm = sub.add_parser("remove", help="删除组件")
    p_rm.add_argument("--component", help="组件类型")
    p_rm.add_argument("--name", help="组件名称")

    # list
    sub.add_parser("list", help="列出组件")

    # set-type
    p_type = sub.add_parser("set-type", help="修改门户类型")
    p_type.add_argument("--type", required=True, choices=["common", "personal", "system", "template"])

    # list-portals
    sub.add_parser("list-portals", help="列出所有门户")

    args = parser.parse_args()

    if args.action == "modify":
        props = json.loads(args.props) if args.props else None
        layout = json.loads(args.layout) if args.layout else None
        r = modify_component(args.api_base, args.token, args.portal_id,
                             component=args.component, name=args.name,
                             props=props, layout=layout)
        print(json.dumps(r, ensure_ascii=False))

    elif args.action == "remove":
        r = remove_component(args.api_base, args.token, args.portal_id,
                             component=args.component, name=args.name)
        print(json.dumps(r, ensure_ascii=False))

    elif args.action == "list":
        r = list_components(args.api_base, args.token, args.portal_id)
        for c in r:
            print(f"  {c['component']:20s} {c['name']:10s} x={c['x']} y={c['y']} w={c['w']} h={c['h']}")

    elif args.action == "set-type":
        r = change_portal_type(args.api_base, args.token, args.portal_id, args.type)
        print(json.dumps(r, ensure_ascii=False))

    elif args.action == "list-portals":
        r = list_portals(args.api_base, args.token)
        for p in r:
            print(f"  {p['id']}  {p['name']:15s}  {p.get('portalCategory',''):10s}  status={p['status']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
