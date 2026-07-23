import json
import urllib.parse
from pathlib import Path


class SecurityChallengeError(RuntimeError):
    pass


class StokenService:
    def __init__(self, session, page_url, cache_dir, user_agent="Mozilla/5.0", timeout=30):
        self.session = session
        self.page_url = page_url
        self.cache_dir = Path(cache_dir)
        self.user_agent = user_agent
        self.timeout = timeout

    def save_text(self, name, text):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / name
        path.write_text(text, encoding="utf-8", errors="ignore")
        return path

    def environment(self, security_url):
        parsed = urllib.parse.urlparse(security_url)
        return {
            "location": {
                "href": security_url,
                "origin": "https://www.zhipin.com",
                "protocol": "https:",
                "host": "www.zhipin.com",
                "hostname": "www.zhipin.com",
                "port": "",
                "pathname": parsed.path,
                "search": f"?{parsed.query}" if parsed.query else "",
                "hash": "",
            },
            "navigator": {
                "userAgent": self.user_agent,
                "platform": "MacIntel",
                "language": "zh-CN",
                "languages": ["zh-CN", "zh", "en"],
                "webdriver": False,
            },
            "screen": {
                "width": 1920,
                "height": 1080,
                "availWidth": 1920,
                "availHeight": 1040,
                "colorDepth": 24,
                "pixelDepth": 24,
            },
            "window": {"origin": "https://www.zhipin.com", "devicePixelRatio": 1},
            "canvas": {"fingerprint": {"toDataURL": {"png": "data:image/png;base64,iVBORw0KGgo="}}},
        }

    def compute_token(self, seed, name, ts):
        from boss_zhipin.iv8_silent import import_iv8_silent

        js_url = f"https://www.zhipin.com/web/common/security-js/{name}.js"
        response = self.session.get(
            js_url, headers={"user-agent": self.user_agent, "referer": self.page_url}, timeout=self.timeout
        )
        response.raise_for_status()
        js_code = response.text
        self.save_text(f"zhipin_security_{name}.js", js_code)
        security_url = "https://www.zhipin.com/web/common/security-check.html?" + urllib.parse.urlencode(
            {"seed": seed, "name": name, "ts": str(ts), "callbackUrl": "", "srcReferer": self.page_url}
        )
        html = f'<html><head><meta charset="utf-8"></head><body><script src="{js_url}"></script></body></html>'
        self.save_text("zhipin_security_check.html", html)
        snapshot = {"baseURL": security_url, "html": html, "headers": [], "resources": {js_url: js_code}}
        iv8 = import_iv8_silent()
        with iv8.JSContext(environment=self.environment(security_url), config={"timezone": "Asia/Shanghai"}) as ctx:
            ctx.expose(snapshot, "snapshot")
            ctx.eval("window.__iv8__.page.load(window.__iv8__.data.snapshot)")
            ctx.eval("window.__iv8__.eventLoop.sleep(100)")
            token = ctx.eval(f"encodeURIComponent((new window.ABC).z({json.dumps(seed)}, {ts}));")
        if not token:
            raise SecurityChallengeError("iv8 未生成 __zp_stoken__")
        self.save_text("zhipin_stoken.txt", str(token))
        return str(token)

    def refresh(self, challenge):
        zp = challenge.get("zpData") or {}
        try:
            seed, name, ts = zp["seed"], zp["name"], int(zp["ts"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SecurityChallengeError("code=37 challenge 缺少 seed/name/ts") from exc
        token = self.compute_token(seed, name, ts)
        values = {"__zp_stoken__": token, "__zp_sseed__": seed, "__zp_sname__": name, "__zp_sts__": ts}
        for cookie_name, value in values.items():
            for cookie in list(self.session.cookies):
                if cookie.name == cookie_name:
                    self.session.cookies.clear(domain=cookie.domain, path=cookie.path, name=cookie.name)
            self.session.cookies.set(cookie_name, str(value), domain=".zhipin.com", path="/")
        return token
