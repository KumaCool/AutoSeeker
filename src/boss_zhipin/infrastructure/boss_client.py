import urllib.parse


API_URL = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/138 Safari/537.36"


class BossApiError(RuntimeError):
    pass


class BossClient:
    def __init__(self, session, criteria, page_size=30, timeout=30, user_agent=DEFAULT_UA):
        self.session = session
        self.criteria = criteria
        self.page_size = page_size
        self.timeout = timeout
        self.user_agent = user_agent

    @property
    def page_url(self):
        query = urllib.parse.quote(self.criteria.keyword)
        return f"https://www.zhipin.com/web/geek/jobs?query={query}&city={self.criteria.city_code}"

    def headers(self):
        return {
            "user-agent": self.user_agent, "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "content-type": "application/x-www-form-urlencoded", "origin": "https://www.zhipin.com",
            "referer": self.page_url, "x-requested-with": "XMLHttpRequest",
        }

    def data(self, page):
        return {
            "scene": "1", "query": self.criteria.keyword, "city": self.criteria.city_code,
            "experience": "", "degree": "", "industry": "", "scale": "", "salary": "",
            "jobType": "", "page": str(page), "pageSize": str(self.page_size),
        }

    def request_page(self, page):
        response = self.session.post(API_URL, headers=self.headers(), data=self.data(page), timeout=self.timeout)
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise BossApiError("BOSS API 返回非 JSON 响应") from exc
        code = payload.get("code")
        if code not in (0, 37):
            raise BossApiError(f"BOSS API code={code}: {payload.get('message') or payload}")
        if code == 37 and not payload.get("zpData"):
            raise BossApiError("BOSS API code=37 缺少 zpData")
        return payload
