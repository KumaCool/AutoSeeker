import json
import os
from pathlib import Path

import requests


API_URL = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"


class AuthError(ValueError):
    pass


def _belongs_to_zhipin(cookie):
    return str(cookie.get("domain", "")).lstrip(".").endswith("zhipin.com")


def validate_cookies(cookies):
    if not isinstance(cookies, list):
        raise AuthError("Cookie 文件必须是浏览器导出的 JSON 数组")
    filtered = [cookie for cookie in cookies if isinstance(cookie, dict) and _belongs_to_zhipin(cookie)]
    if not any(cookie.get("name") == "zp_at" and cookie.get("value") for cookie in filtered):
        raise AuthError("Cookie 中缺少非空 zp_at")
    return filtered


def import_cookies(source: str | Path, destination: str | Path):
    source = Path(source)
    destination = Path(destination)
    cookies = validate_cookies(json.loads(source.read_text(encoding="utf-8")))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    os.chmod(destination, 0o600)
    return len(cookies)


def cookie_dict(cookies):
    if isinstance(cookies, dict):
        return {str(key): str(value) for key, value in cookies.items() if value is not None}
    return {str(item["name"]): str(item["value"]) for item in validate_cookies(cookies)}


def check_cookies(cookies, session=None, timeout=30):
    session = session or requests.Session()
    session.cookies.update(cookie_dict(cookies))
    response = session.post(
        API_URL,
        headers={
            "user-agent": "Mozilla/5.0",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.zhipin.com",
            "referer": "https://www.zhipin.com/web/geek/jobs",
            "x-requested-with": "XMLHttpRequest",
        },
        data={"scene": "1", "query": "前端", "city": "101200100", "page": "1", "pageSize": "1"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    code = payload.get("code")
    if code not in (0, 37):
        raise AuthError(f"BOSS 登录检查失败，业务码={code}")
    return int(code)
