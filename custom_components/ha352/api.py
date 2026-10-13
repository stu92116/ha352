# -*- coding: utf-8 -*-
"""352 智能家电云端客户端（无 HA 依赖，可独立测试）。

协议链路（2026-10-13 从 352Life APK 1.8.0 静态逆向 + 实测验证）：
  1) 352 REST 登录  app.352air.com  -> access_token(60d) / refresh_token / air_token
  2) 阿里 OA loginbyoauth(authCode=access_token) -> OA session sid(24h)
  3) 阿里 IoT 网关 createSessionByAuthCode(OA sid, apiVer=1.0.4) -> iotToken(20h)
  4) /uc/listBindingByAccount 设备列表；/thing/properties/get|set 读写

网关签名：strToSign = POST\naccept\ncontent-md5\ncontent-type\ndate\n
           x-ca-key/nonce/timestamp(按 key 排序)\n + path[?sorted raw query]
           signature = base64(hmac_sha1(APP_SECRET, strToSign))
注意 Java 侧 startsWith("x-ca-") 大小写敏感：X-Ca-Signature-Method / CA_VERSION 不参与签名。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote_plus

import requests

APP_KEY = "27554844"
APP_SECRET = "b66d2c9767cd15a7c5a088341055d134"  # BuildConfig.fySecret
IOT_HOST = "api.link.aliyun.com"
OA_HOST = "sdk.openaccount.aliyun.com"
MX_HOST = "app.352air.com"
MX_APPID = "8d5018f2bc0f11ea8e6388e9fe5ac5b6"
UA_GATEWAY = "ALIYUN-ANDROID-DEMO"
UA_MX = "352Life/1.8.0"

IOT_TOKEN_TTL = 18 * 3600  # iotToken 名义 20h，提前 2h 重建
APIVER_IOT = "1.0.2"
APIVER_CREATE_SESSION = "1.0.4"  # 乌龙: 来自 com.qiyukf.basemodule.BuildConfig


class Ha352Error(Exception):
    """352 云端通用错误。"""


class Ha352AuthError(Ha352Error):
    """账号/密码错误或登录态失效。"""


class Ha352ConnectionError(Ha352Error):
    """网络不可达 / 网关拒绝。"""


def _find_key(obj: Any, key: str) -> Any:
    """在任意嵌套结构里递归找 key（阿里各接口响应层级不稳定）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v
            found = _find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_key(item, key)
            if found is not None:
                return found
    return None


def _extract_device_list(resp: dict) -> list[dict]:
    """listBindingByAccount 响应 -> [ {iotId, productKey, deviceName, status, ...} ]。"""
    data = resp.get("data") if isinstance(resp, dict) else None
    candidates = []
    if isinstance(data, dict):
        for k in ("data", "list", "items", "result"):
            v = data.get(k)
            if isinstance(v, list):
                candidates = v
                break
    elif isinstance(data, list):
        candidates = data
    return [d for d in candidates if isinstance(d, dict) and d.get("iotId")]


def _extract_props(resp: dict) -> dict[str, Any]:
    """/thing/properties/get 响应 -> {identifier: value}。"""
    data = resp.get("data") if isinstance(resp, dict) else None
    props: dict[str, Any] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and "value" in v:
                props[k] = v["value"]
    return props


class Ha352Client:
    """352 账号 -> 阿里 IoT 会话的全托管客户端（同步阻塞，配 executor 使用）。"""

    def __init__(self, account: str, password: str, timeout: int = 20) -> None:
        self.account = str(account)
        self.password = str(password)
        self.timeout = timeout
        self._http = requests.Session()
        self._http.trust_env = False  # 直连，绕开容器/系统代理变量
        self._access_token: str | None = None
        self._refresh_token_352: str | None = None
        self._oa_sid: str | None = None
        self._iot_token: str | None = None
        self._identity_id: str | None = None
        self._iot_refresh: str | None = None
        self._iot_obtained: float = 0.0
        self._lock = threading.Lock()

    # ---------------- 底层 HTTP ----------------

    def _http_date(self) -> str:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    def _gateway(self, host: str, path: str, query: dict[str, Any],
                 body: bytes, content_type: str, accept: str) -> dict:
        """阿里 API Gateway 签名 POST，返回解析后的 JSON dict。"""
        headers = {
            "date": self._http_date(),
            "x-ca-timestamp": str(int(time.time() * 1000)),
            "x-ca-nonce": str(uuid.uuid4()),
            "user-agent": UA_GATEWAY,
            "host": host,
            "x-ca-key": APP_KEY,
            "CA_VERSION": "1",  # 不参与签名
            "content-type": content_type,
            "accept": accept,
            "X-Ca-Signature-Method": "HmacSHA1",  # 大写 X，不参与签名
        }
        if body:
            headers["content-md5"] = base64.b64encode(hashlib.md5(body).digest()).decode()
        signed = {k: v for k, v in headers.items() if k.startswith("x-ca-")}
        str_to_sign = "POST\n" + accept + "\n" + headers.get("content-md5", "") + "\n" \
            + content_type + "\n" + headers["date"] + "\n"
        for k in sorted(signed):
            str_to_sign += f"{k}:{signed[k]}\n"
        str_to_sign += path
        if query:
            # 签名用原始值，按 key 排序；URL 里才做 urlencode
            str_to_sign += "?" + "&".join(
                f"{k}={v}" for k, v in sorted(query.items()) if v != "")
        mac = hmac.new(APP_SECRET.encode(), str_to_sign.encode("utf-8"), hashlib.sha1)
        headers["x-ca-signature"] = base64.b64encode(mac.digest()).decode()
        headers["x-ca-signature-headers"] = ",".join(sorted(signed))

        url = f"https://{host}{path}"
        if query:
            url += "?" + "&".join(
                f"{k}={quote_plus(str(v))}" for k, v in query.items() if v != "")
        try:
            r = self._http.post(url, data=body if body else None,
                                headers=headers, timeout=self.timeout)
        except requests.RequestException as err:
            raise Ha352ConnectionError(f"gateway unreachable: {err}") from err
        try:
            return r.json()
        except ValueError as err:
            raise Ha352ConnectionError(
                f"gateway non-json http={r.status_code}: {r.text[:200]}") from err

    def _mx_headers(self, path: str) -> dict:
        ts = str(int(time.time()))
        sign = hashlib.md5(f"{MX_APPID}{path}{ts}".encode()).hexdigest()
        return {"ts": ts, "sign": sign, "User-Agent": UA_MX,
                "Content-Type": "application/json"}

    # ---------------- 352 REST ----------------

    def _login_352(self) -> None:
        path = "/api/v1/enduser/login"
        try:
            r = self._http.post(
                f"https://{MX_HOST}{path}",
                json={"account": self.account, "password": self.password},
                headers=self._mx_headers(path), timeout=self.timeout)
        except requests.RequestException as err:
            raise Ha352ConnectionError(f"352 login unreachable: {err}") from err
        try:
            resp = r.json()
        except ValueError as err:
            raise Ha352ConnectionError(f"352 login non-json: {r.text[:200]}") from err
        if r.status_code != 200 or resp.get("code") != 0:
            msg = str(resp.get("msg") or resp.get("message") or r.text[:120])
            raise Ha352AuthError(f"352 login failed code={resp.get('code')}: {msg}")
        data = resp.get("data") or {}
        self._access_token = data.get("access_token")
        self._refresh_token_352 = data.get("refresh_token")
        if not self._access_token:
            raise Ha352AuthError("352 login: no access_token in response")

    def mx_get(self, path: str) -> dict:
        """352 自有 REST GET（设备信息/统计等），自动带登录态。"""
        if not self._access_token:
            self._login_352()
        headers = self._mx_headers(path)
        headers["Authorization"] = f"Token {self._access_token}"
        try:
            r = self._http.get(f"https://{MX_HOST}{path}", headers=headers,
                               timeout=self.timeout)
        except requests.RequestException as err:
            raise Ha352ConnectionError(f"mx get unreachable: {err}") from err
        try:
            return r.json()
        except ValueError as err:
            raise Ha352ConnectionError(f"mx get non-json: {r.text[:200]}") from err

    # ---------------- OA / IoT 会话 ----------------

    def _oa_login(self) -> str:
        inner = {"oauthPlateform": 23, "oauthAppKey": APP_KEY,
                 "authCode": self._access_token}
        query = {"loginByOauthRequest": json.dumps(
            inner, separators=(",", ":"), ensure_ascii=False)}
        resp = self._gateway(
            OA_HOST, "/api/prd/loginbyoauth.json", query, b"",
            "application/x-www-form-urlencoded; charset=UTF-8",
            "application/json; charset=UTF-8")
        sid = _find_key(resp, "sid") or _find_key(resp, "sessionId")
        if not sid:
            raise Ha352AuthError(f"OA loginbyoauth no sid: {json.dumps(resp)[:200]}")
        self._oa_sid = sid
        return str(sid)

    def _iot(self, path: str, params: dict, api_ver: str = APIVER_IOT,
             with_token: bool = True) -> dict:
        """阿里 IoT 网关 payload 请求。"""
        request: dict[str, Any] = {"apiVer": api_ver}
        if with_token:
            if not self._iot_token:
                self.build_iot_session()
            request["iotToken"] = self._iot_token
        payload = {
            "id": str(uuid.uuid4()),
            "version": "1.0",
            "request": request,
            "params": params,
        }
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        resp = self._gateway(IOT_HOST, path, {"x-ca-request-id": str(uuid.uuid4())},
                             body, "application/octet-stream; charset=utf-8",
                             "application/json; charset=utf-8")
        code = resp.get("code")
        if code != 200:
            msg = str(resp.get("message") or resp.get("msg") or "")[:200]
            raise Ha352Error(f"iot {path} code={code}: {msg}")
        return resp

    def build_iot_session(self, force: bool = False) -> None:
        """保证 iotToken 可用；过期/强刷时重建整条链（352 登录 -> OA -> iotToken）。"""
        with self._lock:
            if not force and self._iot_token \
                    and time.time() - self._iot_obtained < IOT_TOKEN_TTL:
                return
            try:
                if not self._access_token:
                    self._login_352()
                try:
                    sid = self._oa_login()
                except Ha352Error:
                    # access_token 可能已过期 -> 用密码重新登录再试一次
                    self._login_352()
                    sid = self._oa_login()
                resp = self._iot(
                    "/account/createSessionByAuthCode",
                    {"request": {"authCode": sid, "appKey": APP_KEY,
                                 "accountType": "OA_SESSION"}},
                    api_ver=APIVER_CREATE_SESSION, with_token=False)
                iot_token = resp.get("data", {}).get("iotToken") or _find_key(resp, "iotToken")
                if not iot_token:
                    raise Ha352AuthError(f"createSession no iotToken: {json.dumps(resp)[:200]}")
                self._iot_token = iot_token
                self._identity_id = resp.get("data", {}).get("identityId") \
                    or _find_key(resp, "identityId")
                self._iot_refresh = resp.get("data", {}).get("refreshToken") \
                    or _find_key(resp, "refreshToken")
                self._iot_obtained = time.time()
            except Ha352Error:
                raise
            except Exception as err:  # 防御：任何意外都归一化
                raise Ha352ConnectionError(f"build iot session failed: {err}") from err

    # ---------------- 业务接口（带失效自动重试） ----------------

    def _with_retry(self, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Ha352Error:
            # 登录态失效概率最大：整链重建后重试一次
            self._iot_token = None
            self._access_token = None
            self.build_iot_session(force=True)
            return fn()

    def list_devices(self) -> list[dict]:
        """账号绑定设备列表: [{iotId, productKey, deviceName, status, ...}]。"""
        resp = self._with_retry(lambda: self._iot(
            "/uc/listBindingByAccount", {"pageNo": 1, "pageSize": 50}))
        return _extract_device_list(resp)

    def get_properties(self, iot_id: str) -> dict[str, Any]:
        resp = self._with_retry(lambda: self._iot(
            "/thing/properties/get", {"iotId": iot_id}))
        return _extract_props(resp)

    def set_properties(self, iot_id: str, items: dict[str, Any]) -> None:
        self._with_retry(lambda: self._iot(
            "/thing/properties/set", {"iotId": iot_id, "items": items}))

    def get_thing_info(self, iot_id: str) -> dict:
        """TSL 物模型（调试用）。"""
        resp = self._with_retry(lambda: self._iot("/thing/info/get", {"iotId": iot_id}))
        return resp.get("data") or {}

    def is_online(self, meta: dict) -> bool:
        """listBinding 的 status 字段（1=在线）。"""
        return str(meta.get("status", "1")) == "1"
