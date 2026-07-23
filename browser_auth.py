import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from runtime_paths import COOKIE_FILE, LOG_DIR, PROFILE_DIR


CHROME_LOG = LOG_DIR / "chrome-auth.log"
LOGIN_URL = "https://www.zhipin.com/web/user/"
AUTH_COOKIE_NAMES = {"zp_at"}
CHROME_APP = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def is_logged_in(cookies):
    return any(cookie.get("name") in AUTH_COOKIE_NAMES and cookie.get("value") for cookie in cookies)


def save_cookies(cookies, destination=COOKIE_FILE):
    zhipin_cookies = [
        cookie for cookie in cookies
        if str(cookie.get("domain", "")).lstrip(".").endswith("zhipin.com")
    ]
    if not is_logged_in(zhipin_cookies):
        raise RuntimeError("浏览器会话中没有检测到有效的 BOSS 登录凭据")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(zhipin_cookies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    os.chmod(destination, 0o600)
    return len(zhipin_cookies)


def find_free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def wait_for_chrome(port, timeout=15):
    endpoint = f"http://127.0.0.1:{port}/json/version"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(endpoint, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("Google Chrome 启动超时；请关闭占用项目 profile 的旧窗口后重试")


def start_chrome(headless):
    if not Path(CHROME_APP).exists():
        raise RuntimeError("未找到 /Applications/Google Chrome.app")
    port = find_free_port()
    command = [
        CHROME_APP,
        f"--user-data-dir={PROFILE_DIR}",
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        "--no-first-run",
        "--new-window",
    ]
    if headless:
        command.append("--headless=new")
    command.append(LOGIN_URL)
    CHROME_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_file = CHROME_LOG.open("w", encoding="utf-8")
    process = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT)
    try:
        wait_for_chrome(port)
    except Exception:
        process.terminate()
        log_file.close()
        raise
    return process, port, log_file


def chrome_log_tail():
    if not CHROME_LOG.exists():
        return ""
    lines = CHROME_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-20:])


def get_targets(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_login_target(port):
    targets = get_targets(port)
    page = next(
        (target for target in targets if target.get("type") == "page" and "zhipin.com" in target.get("url", "")),
        None,
    )
    if page:
        return page
    encoded_url = urllib.parse.quote(LOGIN_URL, safe="")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{encoded_url}", method="PUT"
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def read_page_cookies(target):
    try:
        import websocket
    except ImportError as exc:
        raise RuntimeError("缺少 websocket-client，请先运行 ./setup.sh") from exc

    connection = websocket.create_connection(
        target["webSocketDebuggerUrl"], timeout=3, suppress_origin=True
    )
    try:
        request_id = 1
        connection.send(json.dumps({
            "id": request_id,
            "method": "Network.getCookies",
            "params": {"urls": ["https://www.zhipin.com"]},
        }))
        while True:
            payload = json.loads(connection.recv())
            if payload.get("id") != request_id:
                continue
            if payload.get("error"):
                raise RuntimeError(f"读取 Chrome Cookie 失败：{payload['error']}")
            return (payload.get("result") or {}).get("cookies", [])
    finally:
        connection.close()


def refresh_cookies(headless, timeout):
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    chrome_process, port, chrome_log = start_chrome(headless)
    try:
        deadline = time.monotonic() + timeout
        next_status = time.monotonic() + 5
        while time.monotonic() < deadline:
            if chrome_process.poll() is not None:
                detail = chrome_log_tail()
                raise RuntimeError(
                    f"Google Chrome 已提前退出（exit={chrome_process.returncode}）"
                    + (f"\n{detail}" if detail else "")
                )
            try:
                target = ensure_login_target(port)
                cookies = read_page_cookies(target)
            except (OSError, KeyError, ValueError):
                time.sleep(0.5)
                continue
            if is_logged_in(cookies):
                count = save_cookies(cookies)
                print(f"登录状态有效，已自动保存 {count} 个 BOSS Cookie：{COOKIE_FILE}")
                return True
            if headless:
                break
            if time.monotonic() >= next_status:
                print("仍在等待扫码登录，请保持项目专属 Chrome 窗口打开。")
                next_status = time.monotonic() + 5
            time.sleep(1)
        return False
    finally:
        if chrome_process.poll() is None:
            chrome_process.terminate()
            try:
                chrome_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome_process.kill()
        chrome_log.close()


def main():
    parser = argparse.ArgumentParser(description="刷新 BOSS 登录 Cookie")
    parser.add_argument("--headless", action="store_true", help="后台检查已有登录状态")
    parser.add_argument("--timeout", type=int, default=300, help="等待扫码的秒数")
    args = parser.parse_args()

    if not args.headless:
        print("已打开项目专属 Chrome。需要登录时请扫码，成功后脚本会自动继续。")
    try:
        success = refresh_cookies(headless=args.headless, timeout=max(args.timeout, 1))
    except Exception as exc:
        print(f"浏览器登录检查失败：{exc}", file=sys.stderr)
        return 1
    if not success:
        if args.headless:
            print("BOSS 登录已失效，请在终端运行 ./login.sh 完成扫码登录。", file=sys.stderr)
        else:
            print("等待登录超时，未更新 cookies.json。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
