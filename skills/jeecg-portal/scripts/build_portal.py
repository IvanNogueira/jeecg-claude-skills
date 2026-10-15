#!/usr/bin/env python3
"""
全组件门户一键构建脚本

用法:
  python3 build_portal.py --api-base http://host:port/jeecg-boot --token YOUR_TOKEN [--name 门户名称] [--code portal_code]

功能:
  1. 并行查询所有动态数据源（CMS栏目、Design/Online流程、自定义路由、知识库）
  2. 创建门户
  3. 构建包含全部14个组件的 designJson（Web + App 双端）
  4. 保存到门户

也可作为模块导入:
  from build_portal import build_design_json, query_data_sources
"""

import json
import uuid
import urllib.request
import urllib.parse
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor

# ==================== 配置 ====================

ICONS = {
    "JAppCarousel": "/src/assets/images/portalapp/component-cover/carousel.png",
    "JText": "/src/assets/images/portalapp/component-cover/text.png",
    "JAppEnter": "/src/assets/images/portalapp/component-cover/appEnter.png",
    "JCmsNews": "/src/assets/images/portalapp/component-cover/news.png",
    "JSystemNotice": "/src/assets/images/portalapp/component-cover/systemNotice.png",
    "JProcessNotice": "/src/assets/images/portalapp/component-cover/processNotice.png",
    "JMyFlow": "/src/assets/images/portalapp/component-cover/myFlow.png",
    "JMyApplyFlow": "/src/assets/images/portalapp/component-cover/myApplyFlow.png",
    "JCollaPending": "/src/assets/images/portalapp/component-cover/collaPending.png",
    "JSchedule": "/src/assets/images/portalapp/component-cover/schedule.png",
    "JEmail": "/src/assets/images/portalapp/component-cover/email.png",
    "JMeeting": "/src/assets/images/portalapp/component-cover/meeting.png",
    "JKnowledge": "/src/assets/images/portalapp/component-cover/knowledge.png",
    "JIframe": "/src/assets/images/portalapp/component-cover/iframe.png",
}

THEME = {
    # component: (titleBarColor, titleColor, headerStyle)
    "JAppCarousel": ("#1890FF", "#FFFFFF", 3),
    "JText": ("#1890FF", "#000000", 1),
    "JAppEnter": ("#722ED1", "#333333", 2),
    "JCmsNews": ("#13C2C2", "#13C2C2", 2),
    "JSystemNotice": ("#FA541C", "#FA541C", 2),
    "JProcessNotice": ("#EB2F96", "#EB2F96", 2),
    "JMyFlow": ("#1890FF", "#1890FF", 2),
    "JMyApplyFlow": ("#722ED1", "#722ED1", 2),
    "JCollaPending": ("#52C41A", "#52C41A", 2),
    "JSchedule": ("#FAAD14", "#FAAD14", 2),
    "JEmail": ("#2F54EB", "#2F54EB", 2),
    "JMeeting": ("#F5222D", "#F5222D", 2),
    "JKnowledge": ("#597EF7", "#597EF7", 2),
    "JIframe": ("#FF7A45", "#FF7A45", 2),
}

BG_COLORS = ["#1890FF", "#52C41A", "#FAAD14", "#F5222D", "#722ED1",
             "#13C2C2", "#EB2F96", "#FA541C", "#2F54EB", "#A0D911"]

# ==================== API 工具 ====================

def api_request(api_base, token, method, path, body=None):
    """发送 API 请求"""
    url = f"{api_base}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-Access-Token", token)
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(api_base, token, path, params=None):
    if params:
        path += "?" + urllib.parse.urlencode(params)
    return api_request(api_base, token, "GET", path)


def api_post(api_base, token, path, body):
    return api_request(api_base, token, "POST", path, body)

# ==================== 数据源查询 ====================

def query_data_sources(api_base, token):
    """并行查询所有动态数据源，返回字典"""

    results = {}

    def fetch_cms():
        try:
            r = api_get(api_base, token, "/eoa/cms/eoaCmsMenu/treeList")
            if r.get("success"):
                # 递归提取 isShow=1 的栏目
                items = []
                def walk(nodes):
                    for n in (nodes or []):
                        if str(n.get("isShow")) == "1":
                            items.append({"id": n["id"], "menuCode": n["menuCode"], "title": n.get("title") or n.get("menuName")})
                        walk(n.get("children"))
                walk(r["result"] if isinstance(r["result"], list) else [])
                return items
        except Exception as e:
            print(f"[WARN] CMS query failed: {e}")
        return []

    def fetch_design_flows():
        try:
            r = api_get(api_base, token, "/joa/designform/designFormCommuse/roleDegisnList")
            return r.get("result", []) if r.get("success") or r.get("code") == 0 else []
        except Exception as e:
            print(f"[WARN] Design flows query failed: {e}")
            return []

    def fetch_online_flows():
        try:
            r = api_get(api_base, token, "/joa/designform/designFormCommuse/roleOnlineList")
            return r.get("result", []) if r.get("success") or r.get("code") == 0 else []
        except Exception as e:
            print(f"[WARN] Online flows query failed: {e}")
            return []

    def fetch_custom_routes():
        try:
            r = api_get(api_base, token, "/eoa/portalapp/portalCustomRoute/list", {"pageNo": 1, "pageSize": 20})
            return r.get("result", {}).get("records", []) if r.get("success") else []
        except Exception as e:
            print(f"[WARN] Custom routes query failed: {e}")
            return []

    def fetch_knowledge():
        try:
            r = api_get(api_base, token, "/sys/tenant/getCurrentUserTenantForFile")
            result = r.get("result", {})
            if not result or (isinstance(result, dict) and not result):
                return []
            # TODO: 如需进一步查询子文件夹需要 tenantId 和 userId
            return []
        except Exception as e:
            print(f"[WARN] Knowledge query failed: {e}")
            return []

    with ThreadPoolExecutor(max_workers=5) as pool:
        f_cms = pool.submit(fetch_cms)
        f_design = pool.submit(fetch_design_flows)
        f_online = pool.submit(fetch_online_flows)
        f_routes = pool.submit(fetch_custom_routes)
        f_knowledge = pool.submit(fetch_knowledge)

    results["cms"] = f_cms.result()
    results["design_flows"] = f_design.result()
    results["online_flows"] = f_online.result()
    results["custom_routes"] = f_routes.result()
    results["knowledge"] = f_knowledge.result()

    return results

# ==================== designJson 构建 ====================

def uid():
    return uuid.uuid4().hex


def base_props(comp):
    bar_color, title_color, header_style = THEME[comp]
    return {
        "titleBarColor": bar_color,
        "titleColor": title_color,
        "showTitleBar": True,
        "headerStyle": header_style,
        "titleBarFontSize": "default",
    }


def web_comp(comp, name, i, x, y, w, h, extra_props=None):
    p = base_props(comp)
    if extra_props:
        p.update(extra_props)
    return {
        "i": i, "x": x, "y": y, "w": w, "h": h, "static": False,
        "name": name, "component": comp, "icon": ICONS[comp],
        "platform": ["WEB", "APP"], "defaultProps": p,
    }


def app_comp(comp, name, i, y, h, extra_props=None):
    p = base_props(comp)
    if extra_props:
        p.update(extra_props)
    return {
        "i": i, "x": 0, "y": y, "w": 12, "h": h, "static": False,
        "name": name, "component": comp, "icon": ICONS[comp],
        "platform": ["WEB", "APP"], "width": "100%", "height": "100%",
        "defaultProps": p,
    }


def build_app_enter_tabs(data_sources):
    """构建应用快捷入口的 Tab 数据"""
    tabs = []

    # Tab1: OA审批（Design表单流程）
    design_list = []
    for i, f in enumerate(data_sources.get("design_flows", [])[:8]):
        design_list.append({
            "jumpType": "app", "formType": "design",
            "id": f["id"], "desformCode": f.get("desformCode", ""),
            "desformName": f.get("desformName", ""),
            "desformIcon": f.get("desformIcon", ""),
            "procName": f.get("procName", ""),
            "titleExp": f.get("titleExp", ""),
            "appIcon": "", "name": f.get("desformName", ""),
            "imageUrl": "", "imgType": "system",
            "iconBgColor": BG_COLORS[i % len(BG_COLORS)],
            "sortId": str(i),
        })
    if design_list:
        tabs.append({"contentSource": 1, "infoList": design_list, "tabName": "OA审批"})

    # Tab2: 更多审批（Online表单流程）
    online_list = []
    for i, f in enumerate(data_sources.get("online_flows", [])):
        online_list.append({
            "jumpType": "app", "formType": "online",
            "id": f["id"], "desformCode": f.get("desformCode", ""),
            "desformName": f.get("desformName", ""),
            "desformIcon": "", "procName": f.get("procName", ""),
            "titleExp": f.get("titleExp", ""),
            "appIcon": "", "name": f.get("desformName", ""),
            "imageUrl": "", "imgType": "system",
            "iconBgColor": BG_COLORS[(i + 6) % len(BG_COLORS)],
            "sortId": str(i),
        })
    if online_list:
        tabs.append({"contentSource": 1, "infoList": online_list, "tabName": "更多审批"})

    # Tab3: 系统导航（URL）
    url_list = [
        {"jumpType": "url", "webUrl": "/system/user", "appUrl": "", "showPlatform": ["web", "app"],
         "name": "用户管理", "imageUrl": "", "imgType": "system", "iconBgColor": "#1890FF", "id": uid(), "sortId": "0"},
        {"jumpType": "url", "webUrl": "/system/role", "appUrl": "", "showPlatform": ["web", "app"],
         "name": "角色管理", "imageUrl": "", "imgType": "system", "iconBgColor": "#52C41A", "id": uid(), "sortId": "1"},
        {"jumpType": "url", "webUrl": "/system/depart", "appUrl": "", "showPlatform": ["web", "app"],
         "name": "部门管理", "imageUrl": "", "imgType": "system", "iconBgColor": "#FAAD14", "id": uid(), "sortId": "2"},
        {"jumpType": "url", "webUrl": "/system/dict", "appUrl": "", "showPlatform": ["web", "app"],
         "name": "字典管理", "imageUrl": "", "imgType": "system", "iconBgColor": "#F5222D", "id": uid(), "sortId": "3"},
    ]
    tabs.append({"contentSource": 1, "infoList": url_list, "tabName": "系统导航"})

    return tabs


def build_cms_tabs(cms_items):
    """构建新闻动态的 Tab 数据"""
    if not cms_items:
        return 0, [], []  # tabType=0, no tabs
    return 1, [], [
        {"tabName": c["title"], "tabSort": i,
         "infoList": [{"id": c["id"], "menuCode": c["menuCode"], "title": c["title"]}],
         "key": uid()}
        for i, c in enumerate(cms_items)
    ]


def build_design_json(data_sources, portal_name="全组件门户"):
    """构建完整的 designJson，返回 dict"""

    # 为每个组件生成 UUID（Web/App 共享）
    ids = {c: uid() for c in ICONS}

    # 快捷入口
    app_enter_tabs = build_app_enter_tabs(data_sources)
    app_enter_props = {
        "tabType": 1 if len(app_enter_tabs) > 1 else 0,
        "noTabsData": {"contentSource": 1, "infoList": []},
        "tabsData": app_enter_tabs,
        "styleType": 0, "contentBackgroundRadius": "none",
        "contentIconRadius": "whole", "contentIconSize": "default",
        "contentFontSize": "default", "contentFontLines": 1,
        "contentIconAlign": "vertical-center", "contentSpace": "tight",
        "contentItemSpace": "default",
        "colCustomized": False, "colSize": 1,
        "rowCustomized": False, "rowSize": 1,
    }

    # 新闻动态
    cms_tab_type, cms_no_tabs, cms_tabs = build_cms_tabs(data_sources.get("cms", []))
    cms_props = {"tabType": cms_tab_type, "noTabsData": cms_no_tabs, "tabsData": cms_tabs, "showType": 1}

    # 轮播图
    carousel_props = {
        "showName": True, "autoplay": True, "contentPadding": False,
        "textAlign": "bottom", "imgSize": "cover", "textFontSize": "default",
        "list": [
            {"img": "https://picsum.photos/id/1015/1200/400", "name": f"欢迎使用{portal_name}", "webUrl": "", "appUrl": "", "index": 0},
            {"img": "https://picsum.photos/id/1018/1200/400", "name": "高效协同办公平台", "webUrl": "", "appUrl": "", "index": 1},
            {"img": "https://picsum.photos/id/1035/1200/400", "name": "智能流程管理中心", "webUrl": "", "appUrl": "", "index": 2},
        ],
    }

    # 文本
    text_props = {
        "showTitleBar": False,
        "text": f"欢迎使用{portal_name} —— 一站式协同办公平台",
        "fontFamily": "'微软雅黑','宋体','仿宋','楷体','黑体',sans-serif",
        "fontSize": 20, "mobileFontSize": 18, "fontWeight": "bold",
        "color": "#1890FF", "letterSpacing": 2, "textAlign": "center",
    }

    # 组件属性映射
    comp_extra_props = {
        "JAppCarousel": carousel_props,
        "JText": text_props,
        "JAppEnter": app_enter_props,
        "JCmsNews": cms_props,
        "JSystemNotice": {"msgCategory": ["1", "2"], "noticeType": []},
        "JProcessNotice": {},
        "JMyFlow": {"category": [0, 1, 2, 3], "order": [0, 1, 2, 3]},
        "JMyApplyFlow": {},
        "JCollaPending": {"category": [0, 1, 2, 3], "order": [0, 1, 2, 3]},
        "JSchedule": {"mobileMaxCount": 3, "tabType": 1, "singleRange": "week", "multiRange": ["week", "biweek", "month"]},
        "JEmail": {},
        "JMeeting": {},
        "JKnowledge": {"tabType": 0, "noTabsData": [], "tabsData": []},
        "JIframe": {"frameSrc": "https://jeecg.com", "placeholderImg": "", "imgSize": "cover"},
    }

    # Web 端布局
    web_layout = [
        # (component, name, x, y, w, h)
        ("JAppCarousel", "轮播图", 0, 0, 12, 5),
        ("JText", "欢迎语", 0, 5, 12, 2),
        ("JAppEnter", "应用快捷入口", 0, 7, 12, 4),
        ("JCmsNews", "新闻动态", 0, 11, 4, 5),
        ("JSystemNotice", "系统公告", 4, 11, 4, 5),
        ("JProcessNotice", "流程提醒", 8, 11, 4, 5),
        ("JMyFlow", "流程中心", 0, 16, 4, 5),
        ("JMyApplyFlow", "我的申请", 4, 16, 4, 5),
        ("JCollaPending", "协同待办", 8, 16, 4, 5),
        ("JSchedule", "我的计划", 0, 21, 4, 5),
        ("JEmail", "近期邮件", 4, 21, 4, 5),
        ("JMeeting", "会议", 8, 21, 4, 5),
        ("JKnowledge", "知识库", 0, 26, 6, 5),
        ("JIframe", "iframe", 6, 26, 6, 5),
    ]

    web = [web_comp(c, n, ids[c], x, y, w, h, comp_extra_props[c]) for c, n, x, y, w, h in web_layout]

    # App 端布局（高频操作前置）
    app_layout = [
        ("JAppCarousel", "轮播图", 5),
        ("JAppEnter", "应用快捷入口", 5),
        ("JMyFlow", "流程中心", 5),
        ("JCollaPending", "协同待办", 5),
        ("JCmsNews", "新闻动态", 5),
        ("JSystemNotice", "系统公告", 5),
        ("JProcessNotice", "流程提醒", 4),
        ("JMyApplyFlow", "我的申请", 4),
        ("JSchedule", "我的计划", 5),
        ("JEmail", "近期邮件", 4),
        ("JMeeting", "会议", 4),
        ("JKnowledge", "知识库", 5),
        ("JIframe", "iframe", 5),
        ("JText", "欢迎语", 2),
    ]

    app = []
    ay = 0
    for comp, name, h in app_layout:
        app.append(app_comp(comp, name, ids[comp], ay, h, comp_extra_props[comp]))
        ay += h + 1

    return {"webComponentData": web, "appComponentData": app}

# ==================== 主流程 ====================

def create_full_portal(api_base, token, name="全组件门户", code=None):
    """创建包含全部14个组件的门户，返回门户ID"""

    if not code:
        # 简单拼音转换（实际使用时可由调用方提供）
        code = "quan_zu_jian_men_hu"

    # 1. 编码唯一性检查
    print(f"[1/4] 检查编码唯一性: {code}")
    check = api_get(api_base, token, "/sys/duplicate/check", {
        "tableName": "portal_design", "fieldName": "code", "fieldVal": code, "dataId": ""
    })
    if not check.get("success"):
        raise ValueError(f"编码 '{code}' 已存在，请换一个")

    # 2. 查询数据源
    print("[2/4] 并行查询数据源...")
    data_sources = query_data_sources(api_base, token)
    print(f"  CMS栏目: {len(data_sources['cms'])} 个")
    print(f"  Design流程: {len(data_sources['design_flows'])} 个")
    print(f"  Online流程: {len(data_sources['online_flows'])} 个")
    print(f"  自定义路由: {len(data_sources['custom_routes'])} 个")

    # 3. 创建门户
    print(f"[3/4] 创建门户: {name}")
    result = api_post(api_base, token, "/eoa/portalapp/portalDesign/add", {
        "name": name, "code": code, "bizMode": "portal",
        "portalType": "pc,app", "portalCategory": "common",
        "status": "1", "izDefault": "0",
    })
    if not result.get("success"):
        raise RuntimeError(f"创建门户失败: {result.get('message')}")
    portal_id = result["result"]
    print(f"  门户ID: {portal_id}")

    # 4. 构建并保存 designJson
    print("[4/4] 构建 designJson 并保存...")
    design = build_design_json(data_sources, name)
    save_result = api_post(api_base, token, "/eoa/portalapp/portalDesign/edit", {
        "id": portal_id,
        "designJson": json.dumps(design, ensure_ascii=False),
    })
    if not save_result.get("success"):
        raise RuntimeError(f"保存 designJson 失败: {save_result.get('message')}")

    print(f"\n门户创建成功! ID={portal_id}, 包含 14 个组件")
    return portal_id


def main():
    parser = argparse.ArgumentParser(description="全组件门户一键构建")
    parser.add_argument("--api-base", required=True, help="JeecgBoot API 地址")
    parser.add_argument("--token", required=True, help="X-Access-Token")
    parser.add_argument("--name", default="全组件门户", help="门户名称")
    parser.add_argument("--code", default=None, help="门户编码")
    args = parser.parse_args()

    portal_id = create_full_portal(args.api_base, args.token, args.name, args.code)
    print(json.dumps({"success": True, "portalId": portal_id}))


if __name__ == "__main__":
    main()
