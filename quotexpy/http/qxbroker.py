import re, json
import time, requests
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Tuple, Any
import undetected_chromedriver as uc
from quotexpy.exceptions import QuotexAuthError


class Browser(object):
    email = None
    password = None
    headless = None

    base_url = "qxbroker.com"
    https_base_url = f"https://{base_url}"

    def __init__(self, api):
        self.api = api

    def get_cookies_and_ssid(self) -> Tuple[Any, str]:
        try:
            chrome_options = uc.ChromeOptions()
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument('--incognito')
            chrome_options.add_argument('--disable-application-cache')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            browser = uc.Chrome(headless=self.headless, use_subprocess=False, options=chrome_options)
        except TypeError as exc:
            raise SystemError("Chrome is not installed, did you forget?") from exc
        browser.delete_all_cookies()
        time.sleep(5)
        browser.get(f"{self.https_base_url}/en/sign-in")
        if browser.current_url != f"{self.https_base_url}/en/trade":
            print("Pass to try login")
            browser.execute_script('document.getElementsByName("email")[1].value = arguments[0];', self.email)
            browser.execute_script('document.getElementsByName("password")[1].value = arguments[0];', self.password)
            browser.execute_script(
                """document.evaluate("//div[@id='tab-1']/form", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.submit();"""
            )
            time.sleep(5)
        print("Pass cookies")
        try:
            cookies = browser.get_cookies()
            self.api.cookies = cookies
            soup = BeautifulSoup(browser.page_source, "html.parser")
            user_agent = browser.execute_script("return navigator.userAgent;")
            self.api.user_agent = user_agent
        except Exception as exc:
            browser.quit()
            raise QuotexAuthError("Cannot get cookies") from exc
        try:
            script = soup.find_all("script", {"type": "text/javascript"})[1].get_text()
        except Exception as exc:
            browser.delete_all_cookies()
            browser.quit()
            raise QuotexAuthError("incorrect username or password") from exc
        match = re.sub("window.settings = ", "", script.strip().replace(";", ""))
        try:
            ssid = json.loads(match).get("token")
            output_file = Path(".session.json")
            output_file.parent.mkdir(exist_ok=True, parents=True)
            cookiejar = requests.utils.cookiejar_from_dict({c["name"]: c["value"] for c in cookies})
            cookie_string = "; ".join([f"{c.name}={c.value}" for c in cookiejar])
            output_file.write_text(json.dumps({"cookies": cookie_string, "ssid": ssid, "user_agent": user_agent}, indent=4))
            browser.quit()
        except Exception as exc:
            browser.quit()
            raise QuotexAuthError("Cannot get ssid") from exc

        return ssid, cookie_string
