"""
jimureport_core.py — Session、签名、ID生成等基础工具
"""
import base64
import json
import hashlib
import os
import random
import re
import string
import time

import requests

DEFAULT_BASE_URL = "<api_base>"
DEFAULT_TOKEN    = "<token>"
DEFAULT_TENANT   = "2"
# 签名秘钥显式设置（跟 token 同款用法）：知道服务端真实秘钥时直接填这里，填了就不走页面领票。
# 留空则走自动解析。优先级：显式设置(Session参数/此常量) > 环境变量 JIMU_SIGN_SECRET > 页面领票 > 内置默认秘钥
DEFAULT_SIGN_SECRET = ""
SIGN_SECRET      = os.environ.get("JIMU_SIGN_SECRET") or "<SIGNATURE_SECRET>"

# Session(sign_secret=...) 设置后的运行时覆盖（模块级保存，供 _compute_sign 感知）
_sign_secret_override: "str | None" = None

# 服务端把签名票据经 Set-Cookie 下发：Set-Cookie: JM_TICKET=<Base64票据>（v2.5.3+）
# 回退兼容：旧版服务端(v2.5.3之前)是注入页面变量 window._JM_CFG_T = "xxx"（见 resource.ftl / toPath）
_JM_CFG_T_RE = re.compile(r'window\._JM_CFG_T\s*=\s*"([^"]+)"')
# 票据有效期 1~2 小时（±1窗容忍），缓存 45 分钟（半窗）后下次签名前静默重领
_TICKET_TTL_SECONDS = 45 * 60

# 全局票据缓存：(_票据值, 领取时刻)；最近一次 Session 的接入地址与token（惰性领票用）
_ticket_cache: "tuple[str, float] | None" = None
_last_endpoint: "tuple[str, str] | None" = None

SIGNED_PATHS = [
    "/queryFieldBySql", "/executeSelectApi", "/loadTableData",
    "/testConnection",  "/download/image",   "/dictCodeSearch",
    "/getDataSourceByPage", "/getDataSourceById",
    "/exportReportConfig", "/exportAllExcelStream", "/exportPdfStream", "/export/word",
]


def _fetch_ticket() -> "str | None":
    """从设计器页面领一张短期票据：GET {base}/list 后优先取响应 Set-Cookie 的 JM_TICKET，
    取不到再回退页面正则提取 _JM_CFG_T（兼容旧版服务端）。任何一步失败都返回 None
    （调用方回退 SIGN_SECRET），绝不抛异常、绝不阻塞主流程。"""
    if not _last_endpoint:
        return None
    base_url, token = _last_endpoint
    try:
        s = requests.Session()
        s.trust_env = False
        s.verify = False
        r = s.get(base_url + "/list", headers={"X-Access-Token": token}, timeout=10)
        raw = s.cookies.get("JM_TICKET")
        if not raw:
            m = _JM_CFG_T_RE.search(r.text or "")
            raw = m.group(1) if m else None
        if not raw:
            return None
        return base64.b64decode(raw).decode("utf-8")
    except Exception:
        return None


def _refresh_ticket(force: bool = False) -> "str | None":
    """刷新全局票据缓存。force=True 时忽略缓存强制重领（签名失败自愈用）。
    返回当前有效票据；领不到返回 None。"""
    global _ticket_cache
    if not force and _ticket_cache:
        ticket, fetched_at = _ticket_cache
        if time.time() - fetched_at < _TICKET_TTL_SECONDS:
            return ticket
    ticket = _fetch_ticket()
    if ticket:
        _ticket_cache = (ticket, time.time())
    return ticket


def _current_sign_material() -> str:
    """当前签名材料：显式设置(Session参数/DEFAULT_SIGN_SECRET常量) > env > 页面票据 > 内置默认秘钥。"""
    explicit = _sign_secret_override or DEFAULT_SIGN_SECRET
    if explicit:
        return explicit  # 用户显式指定的真实秘钥，永久有效，无需领票
    env_secret = os.environ.get("JIMU_SIGN_SECRET")
    if env_secret:
        return env_secret  # env 指定的真实秘钥，永久有效，无需票据（实时读，不受模块加载时固化影响）
    return _refresh_ticket() or SIGN_SECRET  # 领不到票回退默认值（对旧版服务仍有效）


def _compute_sign(params: dict, secret: "str | None" = None) -> str:
    sp: dict[str, str] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            sp[k] = str(v).lower()
        elif isinstance(v, (int, float)):
            sp[k] = str(v)
        elif isinstance(v, (dict, list)):
            sp[k] = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        else:
            sp[k] = str(v)
    sorted_json = json.dumps(dict(sorted(sp.items())), ensure_ascii=False, separators=(",", ":"))
    material = secret or _current_sign_material()
    return hashlib.md5((sorted_json + material).encode()).hexdigest().upper()


class Session:
    """轻量封装：自动处理签名、Token、代理绕过。"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, token: str = DEFAULT_TOKEN,
                 sign_secret: str = ""):
        self.base_url = base_url.rstrip("/")
        self._s = requests.Session()
        self._s.trust_env = False
        adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=10)
        self._s.mount("http://", adapter)
        self._s.mount("https://", adapter)
        self._s.headers.update({
            "X-Access-Token": token,
            "Content-Type": "application/json",
        })
        # 记录接入点供惰性领票（_fetch_ticket 用；不在构造时请求页面，避免拖慢初始化）
        global _last_endpoint, _sign_secret_override
        _last_endpoint = (self.base_url, token)
        if sign_secret:
            _sign_secret_override = sign_secret  # 显式指定真实秘钥，跳过领票
        self._sign_retry_at = 0.0  # 签名失败自愈：60秒内最多强制重领一次票据（防刷页面，又允许长会话跨窗后再自愈）

    def upload(self, path: str, files: dict, params: dict | None = None) -> dict:
        """multipart 文件上传，临时移除 Content-Type 让 requests 自动生成 boundary。"""
        url = self.base_url + path
        p = dict(params) if params else {}
        p.setdefault("token", self._s.headers.get("X-Access-Token", ""))
        resp = self._s.post(url, files=files, params=p,
                            headers={"Content-Type": None})
        resp.raise_for_status()
        return resp.json()

    def request(self, path: str, data: dict | None = None, method: str = "POST") -> dict:
        for attempt in range(3):
            headers = {}
            need_sign = data is not None and any(path.endswith(p) for p in SIGNED_PATHS)
            url = self.base_url + path
            if method.upper() == "GET":
                params = dict(data) if data else {}
                if need_sign:
                    params["token"] = self._s.headers.get("X-Access-Token", "")
                    headers["X-TIMESTAMP"] = str(int(time.time() * 1000))
                    headers["X-Sign"] = _compute_sign(params)
                resp = self._s.request(method, url, params=params, headers=headers)
            else:
                if need_sign:
                    headers["X-TIMESTAMP"] = str(int(time.time() * 1000))
                    headers["X-Sign"] = _compute_sign(data)
                resp = self._s.request(method, url, json=data, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            if not result.get("success"):
                msg = result.get("message", "")
                if path.endswith("/save") and "Duplicate entry" in msg and "uniq_jmreport_code" in msg:
                    if data and "designerObj" in data:
                        obj = json.loads(data["designerObj"])
                        obj["code"] = gen_code()
                        data = {**data, "designerObj": json.dumps(obj, ensure_ascii=False)}
                    time.sleep(1.1)
                    continue
                # 签名校验失败自愈：强制重领票据后重试（票据跨窗过期/缓存失效的常见场景）
                if need_sign and "签名" in msg and time.time() - self._sign_retry_at > 60:
                    self._sign_retry_at = time.time()
                    _refresh_ticket(force=True)
                    continue
                raise RuntimeError(f"[{path}] 失败: {msg}\n{result}")
            return result
        raise RuntimeError(f"[{path}] 重试3次仍失败")

    def get(self, path: str) -> dict:
        return self.request(path, method="GET")


def gen_id() -> str:
    return str(int(time.time() * 1000) * 1_000_000 + random.randint(100_000, 999_999))


def gen_code() -> str:
    return str(int(time.time() * 1000)) + str(random.randint(100, 999))


def gen_layer() -> str:
    return "lyr_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))


def col_letter(idx: int) -> str:
    result, n = "", idx + 1
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result
