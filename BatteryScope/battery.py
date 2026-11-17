#!/usr/bin/env python3
"""
Hiển thị %pin của thiết bị không dây (tai nghe, chuột, bàn phím, tay cầm...)
Chạy trên Windows, macOS, Linux. Chỉ dùng thư viện có sẵn của Python 3.8+.

Cách dùng:
    python3 battery.py            # in 1 lần
    python3 battery.py --watch 30 # tự cập nhật mỗi 30 giây
"""
import argparse
import glob
import json
import os
import platform
import plistlib
import re
import subprocess
import sys
import time

SYSTEM = platform.system()


def run(cmd, timeout=20):
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, errors="ignore"
        ).stdout
    except Exception:
        return ""


def run_bytes(cmd, timeout=20):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout).stdout
    except Exception:
        return b""


# ----------------------------- macOS -----------------------------
def macos_devices():
    found = []

    # 0) pmset: nguồn ổn định nhất, macOS dùng cho cả menu Âm thanh/Bluetooth
    for line in run(["pmset", "-g", "accps"]).splitlines():
        m = re.match(r"\s*-(.+?)\s+\(id=\d+\)\s+(\d+)%", line)
        if m and not m.group(1).startswith("InternalBattery"):
            found.append((m.group(1).strip(), int(m.group(2)), "pmset"))
    have = {n for n, _, _ in found}

    # 1) Thiết bị Bluetooth đang kết nối (tai nghe, AirPods, chuột, bàn phím...)
    out = run(["system_profiler", "SPBluetoothDataType", "-json"], timeout=40)
    try:
        data = json.loads(out)["SPBluetoothDataType"][0]
    except Exception:
        data = {}
    groups = []
    for key in ("device_connected", "devices_list"):
        if isinstance(data.get(key), list):
            groups += data[key]
    for item in groups:
        for name, info in item.items():
            if not isinstance(info, dict):
                continue
            parts = []
            for k, label in (
                ("device_batteryLevelMain", ""),
                ("device_batteryLevelLeft", "Trái"),
                ("device_batteryLevelRight", "Phải"),
                ("device_batteryLevelCase", "Hộp sạc"),
            ):
                if k in info:
                    m = re.search(r"\d+", str(info[k]))
                    if m:
                        parts.append((label, int(m.group())))
            for label, pct in parts:
                n = f"{name} ({label})" if label else name
                if name not in have:
                    found.append((n, pct, "Bluetooth"))

    # 2) Thiết bị HID có BatteryPercent (Magic Mouse/Keyboard/Trackpad, tay cầm...)
    raw = run_bytes(["ioreg", "-r", "-k", "BatteryPercent", "-a"])
    if raw:
        try:
            items = plistlib.loads(raw)
        except Exception:
            items = []

        def walk(node):
            if isinstance(node, dict):
                if "BatteryPercent" in node:
                    name = node.get("Product") or node.get("DeviceName") or "Thiết bị HID"
                    yield name, int(node["BatteryPercent"])
                for v in node.values():
                    yield from walk(v)
            elif isinstance(node, list):
                for v in node:
                    yield from walk(v)

        for name, pct in walk(items):
            if name not in have:
                found.append((name, pct, "HID"))
    return found


# ----------------------------- Linux -----------------------------
def linux_devices():
    found = []

    # 1) UPower (hỗ trợ chuột, bàn phím, tai nghe, tay cầm qua Bluetooth/2.4GHz)
    if run(["which", "upower"]).strip():
        for path in run(["upower", "-e"]).split():
            if "line_power" in path or "DisplayDevice" in path:
                continue
            info = run(["upower", "-i", path])
            if re.search(r"power supply:\s+yes", info):
                continue  # pin laptop, bỏ qua
            pct = re.search(r"percentage:\s+(\d+)%", info)
            if not pct:
                continue
            name = (
                re.search(r"model:\s+(.+)", info)
                or re.search(r"native-path:\s+(.+)", info)
            )
            found.append(
                (name.group(1).strip() if name else path.split("/")[-1], int(pct.group(1)), "UPower")
            )

    # 2) Dự phòng: /sys/class/power_supply (tay cầm, thiết bị HID)
    for d in glob.glob("/sys/class/power_supply/*"):
        try:
            scope = open(os.path.join(d, "scope")).read().strip()
            if scope != "Device":
                continue
            cap = int(open(os.path.join(d, "capacity")).read().strip())
            try:
                name = open(os.path.join(d, "model_name")).read().strip() or os.path.basename(d)
            except Exception:
                name = os.path.basename(d)
            found.append((name, cap, "sysfs"))
        except Exception:
            continue
    return found


# ----------------------------- Windows -----------------------------
PS_SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$out=@()
Get-PnpDevice -PresentOnly | Where-Object { $_.Class -in 'Bluetooth','HIDClass','MEDIA','AudioEndpoint' } | ForEach-Object {
  $name=$_.FriendlyName
  Get-PnpDeviceProperty -InstanceId $_.InstanceId | Where-Object {
    $_.KeyName -like '{104EA*' -and $_.Data -is [byte] -and $_.Data -le 100
  } | ForEach-Object { $out += [pscustomobject]@{name=$name; pct=[int]$_.Data} }
}
$out | ConvertTo-Json -Compress
"""


def xinput_devices():
    """Tay cầm Xbox/XInput: Windows chỉ cho biết mức pin (đầy/vừa/yếu/hết)."""
    import ctypes

    found = []
    dll = None
    for n in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            dll = ctypes.WinDLL(n)
            break
        except OSError:
            continue
    if not dll:
        return found

    class BatteryInfo(ctypes.Structure):
        _fields_ = [("BatteryType", ctypes.c_ubyte), ("BatteryLevel", ctypes.c_ubyte)]

    levels = {0: 5, 1: 25, 2: 60, 3: 100}  # xấp xỉ, vì Windows không cho %
    names = {0: "hết", 1: "yếu", 2: "vừa", 3: "đầy"}
    for i in range(4):
        info = BatteryInfo()
        if dll.XInputGetBatteryInformation(i, 0, ctypes.byref(info)) == 0:
            if info.BatteryType in (2, 3):  # alkaline / NiMH = không dây
                found.append(
                    (f"Tay cầm XInput #{i + 1} (mức: {names.get(info.BatteryLevel, '?')})",
                     levels.get(info.BatteryLevel, 0), "XInput~"))
    return found


def windows_devices():
    found = []
    out = run(["powershell", "-NoProfile", "-Command", PS_SCRIPT], timeout=60).strip()
    if out:
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for d in data:
                found.append((d["name"], int(d["pct"]), "Bluetooth"))
        except Exception:
            pass
    try:
        found += xinput_devices()
    except Exception:
        pass
    return found


# ----------------------------- Main -----------------------------
def collect():
    if SYSTEM == "Darwin":
        devs = macos_devices()
    elif SYSTEM == "Linux":
        devs = linux_devices()
    elif SYSTEM == "Windows":
        devs = windows_devices()
    else:
        print(f"Hệ điều hành {SYSTEM} chưa được hỗ trợ.")
        return []
    seen, result = set(), []
    for name, pct, src in devs:
        key = (name, pct)
        if key not in seen:
            seen.add(key)
            result.append((name, pct, src))
    return result


def bar(p):
    n = round(p / 10)
    return "█" * n + "░" * (10 - n)


def show():
    devs = collect()
    print(f"\n=== Pin thiết bị không dây ({SYSTEM}) — {time.strftime('%H:%M:%S')} ===")
    if not devs:
        print("Không đọc được pin của thiết bị nào.")
        print("Hãy chắc chắn thiết bị đang bật và đã kết nối. Một số thiết bị không báo pin cho hệ điều hành.")
        return
    for name, pct, src in sorted(devs, key=lambda x: x[1]):
        warn = "  ⚠ pin yếu" if pct <= 20 else ""
        print(f"{name[:42]:<42} {bar(pct)} {pct:>3}%  [{src}]{warn}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, metavar="GIÂY", help="tự cập nhật sau mỗi N giây")
    args = ap.parse_args()
    if not args.watch:
        show()
        return
    try:
        while True:
            show()
            time.sleep(max(args.watch, 5))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
