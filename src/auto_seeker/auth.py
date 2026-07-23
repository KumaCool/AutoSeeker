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
    if isinstance(cookies, list):
        return {
            str(item["name"]): str(item["value"])
            for item in cookies
            if isinstance(item, dict) and item.get("name") and item.get("value") is not None
        }
    raise AuthError("Cookie JSON 必须是对象或数组")


def _parse_cookie_text(text):
    cookies = {}
    for part in text.split(";"):
        if "=" not in part:
            continue
        name, value = part.strip().split("=", 1)
        if name:
            cookies[name] = value
    return cookies


def load_cookie_file(
    path: str | Path,
    legacy_path: str | Path | None = None,
    text_path: str | Path | None = None,
    legacy_text_path: str | Path | None = None,
):
    json_paths = [Path(path)]
    if legacy_path:
        json_paths.append(Path(legacy_path))
    text_paths = [Path(text_path)] if text_path else [Path(path).with_suffix(".txt")]
    if legacy_text_path:
        text_paths.append(Path(legacy_text_path))

    source = next((candidate for candidate in json_paths if candidate.exists()), None)
    if source:
        cookies = cookie_dict(json.loads(source.read_text(encoding="utf-8")))
    else:
        text_source = next((candidate for candidate in text_paths if candidate.exists()), None)
        if text_source is None:
            raise FileNotFoundError(f"缺少 Cookie 文件：{path}")
        cookies = _parse_cookie_text(text_source.read_text(encoding="utf-8").strip())
    if not cookies or any("替换为" in value for value in cookies.values()):
        raise AuthError("Cookie 文件为空或仍是示例内容")
    for name, value in cookies.items():
        try:
            name.encode("latin-1")
            value.encode("latin-1")
        except UnicodeEncodeError as exc:
            raise AuthError(f"Cookie {name!r} 含请求头无法编码的字符") from exc
    return cookies


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
