#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wireless Battery Monitor — Cross-Platform GUI & CLI (Windows, macOS, Linux)
Tự động nhận diện và hiển thị chính xác % pin của các thiết bị không dây:
Tai nghe, Chuột, Bàn phím, Tay cầm chơi game, Loa, Bút cảm ứng...

Hỗ trợ đa giao thức (Zero-dependency mặc định, tự động mở rộng nếu có thư viện):
- macOS:
  1. IORegistry (`ioreg`) — Apple HID, BLE GATT, USB 2.4GHz dongle, AirPods (Trái/Phải/Hộp sạc)
  2. System Profiler (`system_profiler SPBluetoothDataType -json`) — Bluetooth Classic & BLE
  3. Power Management (`pmset -g accps`) — Phụ kiện Bluetooth / Magic Accessories / Tay cầm
- Linux:
  1. Sysfs (`/sys/class/power_supply/`) — HID++, BLE, DualSense/DualShock/Xbox, Logitech 2.4GHz
  2. UPower (`upower -d`) — Chuẩn pin thiết bị ngoại vi trên Desktop Linux
  3. BlueZ (`bluetoothctl`) — Bluetooth Classic (HFP/HSP AT commands) & BLE GATT (0x180F)
  4. Solaar & OpenRazer (`solaar show`, sysfs Razer) — Đầu thu USB 2.4GHz Logitech Unifying/Bolt/Lightspeed & Razer
- Windows:
  1. Windows PnP Device Properties (`Get-PnpDevice` / `DEVPKEY`) — BLE GATT (0x180F), Bluetooth HFP & HID
  2. Windows WMI / CIM (`Win32_Battery` / `Win32_PortableBattery`) — HID Battery & USB 2.4GHz Dongle
  3. Windows XInput Native DLL (`ctypes` -> `XInputGetBatteryInformation`) — Tay cầm Xbox / XInput 2.4GHz & Bluetooth
- Đa nền tảng mở rộng (Optional):
  4. Bleak BLE GATT Scanner (`0x180F` / `0x2A19`) nếu máy đã cài `bleak`.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import threading
from typing import Dict, List, Optional, Tuple

# Kiểm tra Tkinter cho chế độ GUI
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    HAS_TK = True
except Exception:
    HAS_TK = False


# ==============================================================================
# MÔ HÌNH DỮ LIỆU THIẾT BỊ
# ==============================================================================

@dataclass
class WirelessDevice:
    name: str
    category: str          # Headphone, Mouse, Keyboard, Gamepad, Speaker, Stylus, Other
    battery: int           # 0 - 100
    status: str            # Đang dùng, Đang sạc, Đã đầy, Không rõ
    protocol: str          # Giao thức / Nguồn đọc
    address: str = ""      # MAC / Serial / InstanceId (để khử trùng lặp)
    details: str = ""      # Chi tiết phụ (VD: Trái: 85% | Phải: 90% | Hộp: 70%)

    @property
    def icon(self) -> str:
        icons = {
            "Tai nghe": "🎧",
            "Chuột": "🖱️",
            "Bàn phím": "⌨️",
            "Tay cầm": "🎮",
            "Loa": "🔊",
            "Bút / Trackpad": "✒️",
            "Thiết bị khác": "🔋",
        }
        return icons.get(self.category, "🔋")

    @property
    def level_tag(self) -> str:
        if self.battery >= 50:
            return "good"
        if self.battery >= 20:
            return "medium"
        return "low"


# ==============================================================================
# BỘ PHÂN LOẠI THIẾT BỊ TỰ ĐỘNG
# ==============================================================================

def classify_device(name: str, raw_type: str = "") -> str:
    text = f"{name} {raw_type}".lower()

    gamepad_kw = [
        "controller", "gamepad", "joystick", "joy-con", "pro controller",
        "dualsense", "dualshock", "xbox", "xinput", "8bitdo", "gamesir",
        "flydigi", "gulikit", "stadia", "steam controller", "tay cầm"
    ]
    headphone_kw = [
        "airpods", "headphone", "headset", "earbud", "earphone", "buds",
        "wh-1000", "wf-1000", "linkbuds", "bose", "sennheiser", "jabra",
        "jbl", "beats", "soundcore", "arctis", "hyperx", "kraken", "blackshark",
        "barracuda", "g435", "g733", "pro x", "freebuds", "nothing ear",
        "hands-free", "tai nghe"
    ]
    mouse_kw = [
        "mouse", "mx master", "mx anywhere", "mx vertical", "mx ergo",
        "superlight", "g pro", "g304", "g305", "g502", "g703", "g903",
        "deathadder", "viper", "basilisk", "naga", "orochi", "dav3",
        "pulsar", "lamzu", "ninjutso", "zowie", "aerox", "rival",
        "harpe", "gladius", "magic mouse", "chuột"
    ]
    keyboard_kw = [
        "keyboard", "keychron", "mx keys", "mx mechanical", "g915", "g913",
        "g715", "blackwidow", "huntsman", "deathstalker", "nuphy", "akko",
        "monsgeek", "epomaker", "rk61", "rk84", "royal kludge", "aula",
        "leobog", "magic keyboard", "hhkb", "realforce", "lofree", "bàn phím", "kbd"
    ]
    speaker_kw = [
        "speaker", "flip ", "charge ", "xtreme", "boombox", "soundlink",
        "wonderboom", "megaboom", "marshall", "emberton", "stanmore",
        "homepod", "sonos", "anker sound", "loa"
    ]
    stylus_kw = [
        "pencil", "stylus", "pen", "wacom", "trackpad", "magic trackpad"
    ]

    for kw in gamepad_kw:
        if kw in text:
            return "Tay cầm"
    for kw in headphone_kw:
        if kw in text:
            return "Tai nghe"
    for kw in mouse_kw:
        if kw in text:
            return "Chuột"
    for kw in keyboard_kw:
        if kw in text:
            return "Bàn phím"
    for kw in speaker_kw:
        if kw in text:
            return "Loa"
    for kw in stylus_kw:
        if kw in text:
            return "Bút / Trackpad"
    return "Thiết bị khác"


def run_cmd(cmd: List[str], timeout: float = 5.0) -> str:
    """Chạy lệnh hệ thống an toàn, ẩn cửa sổ console trên Windows."""
    try:
        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
        }
        if sys.platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        res = subprocess.run(cmd, **kwargs)
        return res.stdout or ""
    except Exception:
        return ""


def normalize_key(name: str, address: str = "") -> str:
    """Tạo khoá chuẩn hoá để gộp thông tin từ nhiều giao thức không bị trùng."""
    clean_addr = re.sub(r"[^a-fA-F0-9]", "", address).lower()
    if len(clean_addr) == 12:
        return f"mac:{clean_addr}"
    clean_name = re.sub(r"[^a-z0-9]+", "", name.lower())
    return f"name:{clean_name}"


def merge_devices(devices: List[WirelessDevice]) -> List[WirelessDevice]:
    """Khử trùng lặp thông minh và giữ lại bản ghi giàu thông tin nhất."""
    merged: Dict[str, WirelessDevice] = {}
    name_to_key: Dict[str, str] = {}

    for dev in devices:
        if not (0 <= dev.battery <= 100):
            continue
        clean_name = re.sub(r"[^a-z0-9]+", "", dev.name.lower())
        key = normalize_key(dev.name, dev.address)

        # Nếu trùng tên với thiết bị đã có MAC thì gộp chung
        if clean_name in name_to_key:
            existing_key = name_to_key[clean_name]
            if existing_key in merged:
                key = existing_key

        if key not in merged:
            merged[key] = dev
            if clean_name:
                name_to_key[clean_name] = key
        else:
            cur = merged[key]
            # Ưu tiên bản ghi có chi tiết phụ (VD: pin từng bên tai nghe) hoặc có địa chỉ MAC
            if dev.details and not cur.details:
                cur.details = dev.details
            if dev.address and not cur.address:
                cur.address = dev.address
            if cur.category == "Thiết bị khác" and dev.category != "Thiết bị khác":
                cur.category = dev.category
            if cur.status == "Đang dùng" and dev.status in ("Đang sạc", "Đã đầy"):
                cur.status = dev.status
            if dev.protocol not in cur.protocol:
                cur.protocol = f"{cur.protocol} + {dev.protocol}"

    return sorted(merged.values(), key=lambda d: (d.battery, d.name.lower()))


# ==============================================================================
# 1. CÁC GIAO THỨC TRÊN MACOS (DARWIN)
# ==============================================================================

def scan_macos_ioreg() -> List[WirelessDevice]:
    """Đọc IORegistry: hỗ trợ Apple HID, BLE GATT, USB 2.4GHz HID và AirPods."""
    devices: List[WirelessDevice] = []
    out = run_cmd(["ioreg", "-r", "-l", "-w", "0"], timeout=6.0)
    if not out:
        return devices

    blocks = re.split(r"\n(?=\+\-o |\s*\+\-o )", out)
    for block in blocks:
        if "BatteryPercent" not in block:
            continue
        # Bỏ qua pin nội bộ của MacBook
        if "AppleSmartBattery" in block or "InternalBattery" in block:
            continue

        prod_m = re.search(r'"Product"\s*=\s*"([^"]+)"', block)
        name_m = re.search(r'"DeviceName"\s*=\s*"([^"]+)"', block)
        name = (prod_m.group(1) if prod_m else (name_m.group(1) if name_m else "")).strip()
        if not name:
            continue

        bat_m = re.search(r'"BatteryPercent"\s*=\s*(\d+)', block)
        left_m = re.search(r'"BatteryPercentLeft"\s*=\s*(\d+)', block)
        right_m = re.search(r'"BatteryPercentRight"\s*=\s*(\d+)', block)
        case_m = re.search(r'"BatteryPercentCase"\s*=\s*(\d+)', block)

        details_parts = []
        levels = []
        if left_m and int(left_m.group(1)) > 0:
            lv = int(left_m.group(1))
            levels.append(lv)
            details_parts.append(f"Trái: {lv}%")
        if right_m and int(right_m.group(1)) > 0:
            rv = int(right_m.group(1))
            levels.append(rv)
            details_parts.append(f"Phải: {rv}%")
        if case_m and int(case_m.group(1)) > 0:
            cv = int(case_m.group(1))
            details_parts.append(f"Hộp: {cv}%")

        if bat_m:
            main_bat = int(bat_m.group(1))
        elif levels:
            main_bat = min(levels)
        else:
            continue

        transport_m = re.search(r'"Transport"\s*=\s*"([^"]+)"', block)
        transport = transport_m.group(1) if transport_m else "HID/IOReg"
        addr_m = re.search(r'"DeviceAddress"\s*=\s*"([^"]+)"', block)
        addr = addr_m.group(1) if addr_m else ""

        charging = "Đang dùng"
        if re.search(r'"BatteryStatusFlags"\s*=\s*[1-9]', block) or re.search(r'"IsCharging"\s*=\s*Yes', block):
            charging = "Đang sạc"

        devices.append(
            WirelessDevice(
                name=name,
                category=classify_device(name, transport),
                battery=main_bat,
                status=charging,
                protocol=f"macOS IOReg ({transport})",
                address=addr,
                details=" | ".join(details_parts),
            )
        )
    return devices


def scan_macos_system_profiler() -> List[WirelessDevice]:
    """Đọc system_profiler SPBluetoothDataType (Bluetooth Classic, BLE, AirPods/Beats)."""
    devices: List[WirelessDevice] = []
    out = run_cmd(["system_profiler", "SPBluetoothDataType", "-json"], timeout=6.0)
    if not out:
        return devices

    try:
        data = json.loads(out)
        bt_list = data.get("SPBluetoothDataType", [])
        for entry in bt_list:
            connected = entry.get("device_connected", [])
            if isinstance(connected, dict):
                connected = [connected]
            for item in connected:
                if not isinstance(item, dict):
                    continue
                for dev_name, info in item.items():
                    if not isinstance(info, dict):
                        continue
                    main_lvl = info.get("device_batteryLevelMain") or info.get("device_batteryLevel")
                    left_lvl = info.get("device_batteryLevelLeft")
                    right_lvl = info.get("device_batteryLevelRight")
                    case_lvl = info.get("device_batteryLevelCase")

                    def parse_pct(val: Optional[str]) -> Optional[int]:
                        if val is None:
                            return None
                        m = re.search(r"(\d+)", str(val))
                        return int(m.group(1)) if m else None

                    p_main = parse_pct(main_lvl)
                    p_left = parse_pct(left_lvl)
                    p_right = parse_pct(right_lvl)
                    p_case = parse_pct(case_lvl)

                    details = []
                    valid_ears = [x for x in (p_left, p_right) if x is not None]
                    if p_left is not None:
                        details.append(f"Trái: {p_left}%")
                    if p_right is not None:
                        details.append(f"Phải: {p_right}%")
                    if p_case is not None:
                        details.append(f"Hộp: {p_case}%")

                    battery = p_main if p_main is not None else (min(valid_ears) if valid_ears else None)
                    if battery is None:
                        continue

                    minor_type = str(info.get("device_minorType", ""))
                    addr = str(info.get("device_address", ""))
                    devices.append(
                        WirelessDevice(
                            name=dev_name,
                            category=classify_device(dev_name, minor_type),
                            battery=battery,
                            status="Đang dùng",
                            protocol="macOS Bluetooth",
                            address=addr,
                            details=" | ".join(details),
                        )
                    )
    except Exception:
        pass
    return devices


def scan_macos_pmset() -> List[WirelessDevice]:
    """Đọc pmset -g accps (Quản lý nguồn phụ kiện của macOS)."""
    devices: List[WirelessDevice] = []
    out = run_cmd(["pmset", "-g", "accps"], timeout=4.0)
    if not out:
        return devices

    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        if "InternalBattery" in line:
            continue
        # Ví dụ: -Magic Mouse (id=...) 84%; discharging
        m = re.match(r"^-(.+?)\s*(?:\([^)]*\))?\s+(\d+)%;\s*([^;]+)", line)
        if m:
            name = m.group(1).strip()
            pct = int(m.group(2))
            raw_state = m.group(3).strip().lower()
            status = "Đang sạc" if "charg" in raw_state and "discharg" not in raw_state else (
                "Đã đầy" if "charged" in raw_state or "full" in raw_state else "Đang dùng"
            )
            devices.append(
                WirelessDevice(
                    name=name,
                    category=classify_device(name),
                    battery=pct,
                    status=status,
                    protocol="macOS PMSet",
                )
            )
    return devices


# ==============================================================================
# 2. CÁC GIAO THỨC TRÊN LINUX
# ==============================================================================

def scan_linux_sysfs() -> List[WirelessDevice]:
    """Đọc trực tiếp từ Kernel /sys/class/power_supply (nhanh nhất, không phụ thuộc gói ngoài)."""
    devices: List[WirelessDevice] = []
    base = Path("/sys/class/power_supply")
    if not base.exists():
        return devices

    for ps_dir in base.iterdir():
        try:
            ps_name = ps_dir.name
            # Bỏ qua pin laptop và sạc AC
            if re.match(r"^(BAT\d+|AC|ACAD|ADP\d+|Mains|ucsi-source.*)$", ps_name, re.IGNORECASE):
                continue

            scope_file = ps_dir / "scope"
            if scope_file.exists():
                scope = scope_file.read_text(errors="ignore").strip().lower()
                if scope == "system":
                    continue

            cap_file = ps_dir / "capacity"
            if not cap_file.exists():
                continue
            pct = int(cap_file.read_text(errors="ignore").strip())

            model_file = ps_dir / "model_name"
            manuf_file = ps_dir / "manufacturer"
            status_file = ps_dir / "status"
            serial_file = ps_dir / "serial_number"

            model = model_file.read_text(errors="ignore").strip() if model_file.exists() else ""
            manuf = manuf_file.read_text(errors="ignore").strip() if manuf_file.exists() else ""
            raw_status = status_file.read_text(errors="ignore").strip().lower() if status_file.exists() else ""
            serial = serial_file.read_text(errors="ignore").strip() if serial_file.exists() else ps_name

            name = model or f"{manuf} {ps_name}".strip()
            if manuf and model and manuf.lower() not in model.lower():
                name = f"{manuf} {model}"

            status = "Đang dùng"
            if "charging" in raw_status and "discharging" not in raw_status:
                status = "Đang sạc"
            elif "full" in raw_status:
                status = "Đã đầy"

            proto = "Linux Kernel Sysfs"
            if "hidpp" in ps_name.lower():
                proto = "Logitech HID++ (Sysfs)"
            elif "sony" in ps_name.lower() or "ps-controller" in ps_name.lower():
                proto = "PlayStation HID (Sysfs)"
            elif "hid-" in ps_name.lower():
                proto = "HID Battery (Sysfs)"

            devices.append(
                WirelessDevice(
                    name=name,
                    category=classify_device(name, ps_name),
                    battery=pct,
                    status=status,
                    protocol=proto,
                    address=serial,
                )
            )
        except Exception:
            continue
    return devices


def scan_linux_upower() -> List[WirelessDevice]:
    """Đọc UPower daemon (chuẩn thiết bị ngoại vi trên Ubuntu/Fedora/Arch)."""
    devices: List[WirelessDevice] = []
    if not shutil.which("upower"):
        return devices

    out = run_cmd(["upower", "-d"], timeout=5.0)
    if not out:
        return devices

    blocks = out.split("\nDevice: ")
    for block in blocks[1:]:
        lines = block.splitlines()
        dev_path = lines[0].strip() if lines else ""
        if "line_power" in dev_path or "DisplayDevice" in dev_path or "/battery_BAT" in dev_path:
            continue

        model = ""
        vendor = ""
        serial = ""
        dev_type = ""
        pct = None
        state = "Đang dùng"
        rechargeable = True

        for line in lines[1:]:
            s = line.strip()
            if s.startswith(("mouse", "keyboard", "gaming-input", "headphones", "headset", "speakers", "bluetooth-generic", "tablet", "pda", "phone")):
                dev_type = s.split()[0]
            elif s.startswith("vendor:"):
                vendor = s.split(":", 1)[1].strip()
            elif s.startswith("model:"):
                model = s.split(":", 1)[1].strip()
            elif s.startswith("serial:"):
                serial = s.split(":", 1)[1].strip()
            elif s.startswith("percentage:"):
                m = re.search(r"(\d+)", s)
                if m:
                    pct = int(m.group(1))
            elif s.startswith("state:"):
                raw_st = s.split(":", 1)[1].strip().lower()
                if "charging" in raw_st and "discharging" not in raw_st:
                    state = "Đang sạc"
                elif "fully-charged" in raw_st:
                    state = "Đã đầy"
            elif s.startswith("native-path:") and "BAT" in s:
                rechargeable = False

        if not rechargeable or pct is None:
            continue

        name = model or dev_type or dev_path.split("/")[-1]
        if vendor and model and vendor.lower() not in model.lower():
            name = f"{vendor} {model}"

        devices.append(
            WirelessDevice(
                name=name,
                category=classify_device(name, dev_type),
                battery=pct,
                status=state,
                protocol="Linux UPower",
                address=serial,
            )
        )
    return devices


def scan_linux_bluez() -> List[WirelessDevice]:
    """Đọc BlueZ qua bluetoothctl (hỗ trợ tai nghe HFP AT+IPHONEACCEV và BLE GATT 0x180F)."""
    devices: List[WirelessDevice] = []
    if not shutil.which("bluetoothctl"):
        return devices

    out = run_cmd(["bluetoothctl", "devices", "Connected"], timeout=4.0)
    if not out.strip():
        # Thử fallback cho bản bluetoothctl cũ không hỗ trợ tham số 'Connected'
        out = run_cmd(["bluetoothctl", "devices"], timeout=4.0)

    for line in out.splitlines():
        m = re.match(r"^Device\s+([0-9A-Fa-f:]{17})\s+(.+)$", line.strip())
        if not m:
            continue
        mac, name = m.group(1), m.group(2).strip()
        info = run_cmd(["bluetoothctl", "info", mac], timeout=3.0)
        if "Connected: yes" not in info:
            continue

        # Ví dụ: Battery Percentage: 0x5a (90)
        bat_m = re.search(r"Battery Percentage:\s*(?:0x[0-9a-fA-F]+\s*)?\((\d+)\)", info)
        if not bat_m:
            continue
        pct = int(bat_m.group(1))
        icon_m = re.search(r"Icon:\s*(.+)", info)
        icon_hint = icon_m.group(1).strip() if icon_m else ""

        devices.append(
            WirelessDevice(
                name=name,
                category=classify_device(name, icon_hint),
                battery=pct,
                status="Đang dùng",
                protocol="BlueZ Bluetooth (GATT/HFP)",
                address=mac,
            )
        )
    return devices


def scan_solaar_24ghz() -> List[WirelessDevice]:
    """Đọc thiết bị Logitech 2.4GHz Unifying / Bolt / Lightspeed qua Solaar CLI (nếu có)."""
    devices: List[WirelessDevice] = []
    if not shutil.which("solaar"):
        return devices

    out = run_cmd(["solaar", "show"], timeout=5.0)
    if not out:
        return devices

    current_name = ""
    current_kind = ""
    current_serial = ""
    for line in out.splitlines():
        dev_m = re.match(r"^\s+\d+:\s+(.+)$", line)
        if dev_m:
            current_name = dev_m.group(1).strip()
            current_kind = ""
            current_serial = ""
            continue
        if "Kind" in line and ":" in line:
            current_kind = line.split(":", 1)[1].strip()
        elif "Serial" in line and ":" in line:
            current_serial = line.split(":", 1)[1].strip()
        elif "Battery" in line and ":" in line and current_name:
            bat_m = re.search(r"(\d+)%", line)
            if bat_m:
                pct = int(bat_m.group(1))
                status = "Đang sạc" if "recharging" in line.lower() else (
                    "Đã đầy" if "full" in line.lower() else "Đang dùng"
                )
                devices.append(
                    WirelessDevice(
                        name=f"Logitech {current_name}" if "logitech" not in current_name.lower() else current_name,
                        category=classify_device(current_name, current_kind),
                        battery=pct,
                        status=status,
                        protocol="Logitech 2.4GHz HID++ (Solaar)",
                        address=current_serial,
                    )
                )
    return devices


# ==============================================================================
# 3. CÁC GIAO THỨC TRÊN WINDOWS (WIN32)
# ==============================================================================

def scan_windows_powershell() -> List[WirelessDevice]:
    """
    Quét trên Windows qua PowerShell:
    1. PnP DEVPKEY_Bluetooth_Battery ({104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2)
    2. PnP Hands-Free HFP Headset Battery ({F0E20F09-D97A-49A9-8046-BB6E22E6BB2E} 2)
    3. WMI / CIM Win32_Battery (lọc bỏ pin trong của Laptop)
    """
    devices: List[WirelessDevice] = []
    ps_script = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$results = @()

$propKeys = @(
    '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2',
    '{F0E20F09-D97A-49A9-8046-BB6E22E6BB2E} 2'
)

$pnpDevs = Get-PnpDevice -PresentOnly | Where-Object {
    $_.Class -in @('Bluetooth', 'BluetoothLE', 'HIDClass', 'Mouse', 'Keyboard', 'Media', 'AudioEndpoint', 'System', 'XnaComposite', 'XboxComposite')
}

foreach ($dev in $pnpDevs) {
    foreach ($key in $propKeys) {
        $prop = Get-PnpDeviceProperty -InstanceId $dev.InstanceId -KeyName $key -ErrorAction SilentlyContinue
        if ($null -ne $prop -and $null -ne $prop.Data -and $prop.Type -ne 'Empty') {
            $val = [int]$prop.Data
            if ($val -ge 0 -and $val -le 100) {
                $proto = if ($key -like '*104EA319*') { 'Windows PnP (BLE/HID)' } else { 'Windows Bluetooth HFP' }
                $results += [PSCustomObject]@{
                    Name = [string]$dev.FriendlyName
                    Class = [string]$dev.Class
                    Battery = $val
                    Status = 'Đang dùng'
                    Protocol = $proto
                    Address = [string]$dev.InstanceId
                }
                break
            }
        }
    }
}

$wmiBats = Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue
foreach ($b in $wmiBats) {
    $bName = [string]$b.Name
    $bId = [string]$b.DeviceID
    if ($bName -notmatch 'Internal|ACPI|Microsoft ACPI' -and $bId -notmatch 'ACPI') {
        $pct = [int]$b.EstimatedChargeRemaining
        if ($pct -ge 0 -and $pct -le 100) {
            $st = if ($b.BatteryStatus -eq 2) { 'Đang sạc' } elseif ($b.BatteryStatus -eq 3) { 'Đã đầy' } else { 'Đang dùng' }
            $results += [PSCustomObject]@{
                Name = if ($bName) { $bName } else { 'Thiết bị HID không dây' }
                Class = 'HIDBattery'
                Battery = $pct
                Status = $st
                Protocol = 'Windows WMI HID Battery'
                Address = $bId
            }
        }
    }
}

$results | ConvertTo-Json -Compress
"""
    out = run_cmd(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script], timeout=8.0)
    if not out.strip():
        return devices

    try:
        parsed = json.loads(out.strip())
        if isinstance(parsed, dict):
            parsed = [parsed]
        for item in parsed:
            if not isinstance(item, dict):
                continue
            name = str(item.get("Name") or "Thiết bị không dây").strip()
            dev_class = str(item.get("Class") or "")
            pct = int(item.get("Battery", -1))
            if not (0 <= pct <= 100):
                continue
            devices.append(
                WirelessDevice(
                    name=name,
                    category=classify_device(name, dev_class),
                    battery=pct,
                    status=str(item.get("Status") or "Đang dùng"),
                    protocol=str(item.get("Protocol") or "Windows PnP"),
                    address=str(item.get("Address") or ""),
                )
            )
    except Exception:
        pass
    return devices


def scan_windows_xinput() -> List[WirelessDevice]:
    """
    Đọc trực tiếp pin tay cầm chơi game Xbox / XInput (2.4GHz Wireless Adapter & Bluetooth)
    bằng cách gọi thẳng DLL hệ thống của Windows qua ctypes.
    """
    devices: List[WirelessDevice] = []
    if not sys.platform.startswith("win"):
        return devices

    xinput_dll = None
    for dll_name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
        try:
            xinput_dll = ctypes.WinDLL(dll_name)
            break
        except Exception:
            continue

    if xinput_dll is None or not hasattr(xinput_dll, "XInputGetBatteryInformation"):
        return devices

    class XINPUT_BATTERY_INFORMATION(ctypes.Structure):
        _fields_ = [("BatteryType", ctypes.c_ubyte), ("BatteryLevel", ctypes.c_ubyte)]

    # BATTERY_DEVTYPE_GAMEPAD = 0x00
    # BatteryType: 0=Disconnected, 1=Wired, 2=Alkaline, 3=NiMH
    # BatteryLevel: 0=Empty(10%), 1=Low(30%), 2=Medium(65%), 3=Full(100%)
    level_map = {
        0: (10, "Mức: Rất yếu (Empty)"),
        1: (30, "Mức: Thấp (Low)"),
        2: (65, "Mức: Trung bình (Medium)"),
        3: (100, "Mức: Đầy (Full)"),
    }

    for user_idx in range(4):
        try:
            bat_info = XINPUT_BATTERY_INFORMATION()
            res = xinput_dll.XInputGetBatteryInformation(
                ctypes.c_uint(user_idx),
                ctypes.c_ubyte(0),
                ctypes.byref(bat_info),
            )
            # ERROR_SUCCESS == 0, BatteryType in (2: Alkaline, 3: NiMH)
            if res == 0 and bat_info.BatteryType in (2, 3):
                pct, level_desc = level_map.get(bat_info.BatteryLevel, (50, "Mức: Đang hoạt động"))
                chem = "Pin sạc NiMH/Li-ion" if bat_info.BatteryType == 3 else "Pin Alkaline"
                devices.append(
                    WirelessDevice(
                        name=f"Tay cầm Xbox / XInput #{user_idx + 1}",
                        category="Tay cầm",
                        battery=pct,
                        status="Đang dùng",
                        protocol="Windows XInput Native DLL",
                        address=f"xinput_pad_{user_idx}",
                        details=f"{level_desc} | {chem}",
                    )
                )
        except Exception:
            continue
    return devices


# ==============================================================================
# BỘ ĐIỀU PHỐI QUÉT ĐA HỆ ĐIỀU HÀNH
# ==============================================================================

def scan_all_wireless_devices(include_demo: bool = False) -> Tuple[List[WirelessDevice], List[str]]:
    """
    Quét tất cả giao thức tương thích với hệ điều hành hiện tại.
    Trả về: (Danh sách thiết bị đã gộp, Danh sách các giao thức đã quét).
    """
    raw_devices: List[WirelessDevice] = []
    active_protocols: List[str] = []

    sys_name = sys.platform.lower()
    if sys_name == "darwin":
        active_protocols = ["IORegistry (BLE/HID/2.4GHz)", "SPBluetoothDataType", "PMSet Accessory", "Solaar HID++"]
        raw_devices.extend(scan_macos_ioreg())
        raw_devices.extend(scan_macos_system_profiler())
        raw_devices.extend(scan_macos_pmset())
        raw_devices.extend(scan_solaar_24ghz())
    elif sys_name.startswith("win"):
        active_protocols = ["Windows PnP DEVPKEY (BLE/HFP/HID)", "WMI HID Battery", "XInput Gamepad DLL", "Solaar HID++"]
        raw_devices.extend(scan_windows_powershell())
        raw_devices.extend(scan_windows_xinput())
        raw_devices.extend(scan_solaar_24ghz())
    else:
        active_protocols = ["Linux Kernel Sysfs", "UPower Daemon", "BlueZ (GATT/HFP)", "Solaar 2.4GHz HID++"]
        raw_devices.extend(scan_linux_sysfs())
        raw_devices.extend(scan_linux_upower())
        raw_devices.extend(scan_linux_bluez())
        raw_devices.extend(scan_solaar_24ghz())

    merged = merge_devices(raw_devices)

    if include_demo and not merged:
        merged = [
            WirelessDevice(
                name="AirPods Pro (Gen 2)",
                category="Tai nghe",
                battery=82,
                status="Đang dùng",
                protocol="Apple HID / BLE GATT (Demo)",
                address="AA:BB:CC:11:22:33",
                details="Trái: 82% | Phải: 88% | Hộp: 95%",
            ),
            WirelessDevice(
                name="Logitech G Pro X Superlight 2",
                category="Chuột",
                battery=64,
                status="Đang dùng",
                protocol="USB 2.4GHz Lightspeed HID++ (Demo)",
                address="logi_superlight_2",
                details="Polling Rate: 2000Hz",
            ),
            WirelessDevice(
                name="Keychron K2 Pro Wireless",
                category="Bàn phím",
                battery=41,
                status="Đang sạc",
                protocol="BLE GATT 0x180F (Demo)",
                address="AA:BB:CC:44:55:66",
            ),
            WirelessDevice(
                name="Sony DualSense Wireless Controller",
                category="Tay cầm",
                battery=15,
                status="Đang dùng",
                protocol="Bluetooth HID Gamepad (Demo)",
                address="AA:BB:CC:77:88:99",
                details="Cảnh báo pin yếu (< 20%)",
            ),
        ]

    return merged, active_protocols


# ==============================================================================
# CHẾ ĐỘ TERMINAL CLI (BẢNG THỐNG KÊ & PHẦN TRĂM)
# ==============================================================================

def print_cli_report(devices: List[WirelessDevice], protocols: List[str]) -> None:
    os_label = f"{platform.system()} {platform.release()} ({platform.machine()})"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 98)
    print(f" BÁO CÁO PIN THIẾT BỊ KHÔNG DÂY | HỆ ĐIỀU HÀNH: {os_label}")
    print(f" Thời gian quét : {now_str}")
    print(f" Giao thức quét : {', '.join(protocols)}")
    print("=" * 98)

    if not devices:
        print(" [!] Hiện không phát hiện thiết bị không dây nào đang báo cáo mức pin.")
        print("     Gợi ý: Hãy bật nguồn thiết bị hoặc chạy kèm cờ '--demo' để xem giao diện mẫu.")
        print("=" * 98)
        return

    header = f" {'#':<2} | {'Thiết bị':<32} | {'Phân loại':<12} | {'% Pin':>7} | {'Trạng thái':<10} | {'Giao thức / Chi tiết'}"
    print(header)
    print("-" * 98)

    for idx, d in enumerate(devices, 1):
        extra = f"{d.protocol}" + (f" ({d.details})" if d.details else "")
        pct_str = f"{d.battery}%"
        print(f" {idx:<2} | {d.name[:32]:<32} | {d.category:<12} | {pct_str:>7} | {d.status:<10} | {extra}")

    print("-" * 98)
    total = len(devices)
    avg_bat = sum(d.battery for d in devices) / total
    low_count = sum(1 for d in devices if d.battery < 20)
    min_dev = min(devices, key=lambda x: x.battery)
    max_dev = max(devices, key=lambda x: x.battery)

    print(
        f" THỐNG KÊ: Tổng cộng: {total} thiết bị | Pin TB: {avg_bat:.1f}% | "
        f"Pin thấp (<20%): {low_count} ({low_count * 100.0 / total:.1f}%) | "
        f"Thấp nhất: {min_dev.name} ({min_dev.battery}%) | Cao nhất: {max_dev.name} ({max_dev.battery}%)"
    )
    print("=" * 98)


# ==============================================================================
# GIAO DIỆN ĐỒ HOẠ (GUI TKINTER ĐA NỀN TẢNG)
# ==============================================================================

class WirelessBatteryApp:
    BG_MAIN = "#0F172A"
    BG_CARD = "#1E293B"
    BG_HEADER = "#111827"
    FG_PRIMARY = "#F8FAFC"
    FG_SECONDARY = "#94A3B8"
    ACCENT_BLUE = "#38BDF8"
    COLOR_GOOD = "#22C55E"
    COLOR_WARN = "#F59E0B"
    COLOR_LOW = "#EF4444"

    def __init__(self, root: "tk.Tk", start_with_demo: bool = False) -> None:
        self.root = root
        self.root.title("Quản Lý Pin Thiết Bị Không Dây — Đa Nền Tảng (Windows / macOS / Linux)")
        self.root.geometry("940x640")
        self.root.minsize(780, 500)
        self.root.configure(bg=self.BG_MAIN)

        self.devices: List[WirelessDevice] = []
        self.protocols: List[str] = []
        self.is_scanning = False
        self.demo_var = tk.BooleanVar(value=start_with_demo)
        self.topmost_var = tk.BooleanVar(value=False)
        self.interval_var = tk.StringVar(value="30 giây")
        self.after_job: Optional[str] = None

        self._setup_styles()
        self._build_ui()
        self.trigger_scan()

    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview",
            background=self.BG_CARD,
            foreground=self.FG_PRIMARY,
            fieldbackground=self.BG_CARD,
            rowheight=36,
            borderwidth=0,
            font=("Segoe UI" if sys.platform.startswith("win") else "Helvetica", 11),
        )
        style.configure(
            "Treeview.Heading",
            background="#334155",
            foreground=self.FG_PRIMARY,
            relief="flat",
            font=("Segoe UI" if sys.platform.startswith("win") else "Helvetica", 11, "bold"),
        )
        style.map("Treeview", background=[("selected", "#2563EB")], foreground=[("selected", "#FFFFFF")])

    def _build_ui(self) -> None:
        font_family = "Segoe UI" if sys.platform.startswith("win") else (
            "SF Pro Text" if sys.platform == "darwin" else "DejaVu Sans"
        )

        # 1. Thanh tiêu đề & nút điều khiển
        header = tk.Frame(self.root, bg=self.BG_HEADER, padx=18, pady=14)
        header.pack(fill="x")

        title_box = tk.Frame(header, bg=self.BG_HEADER)
        title_box.pack(side="left", fill="y")

        tk.Label(
            title_box,
            text="🔋 Trình Theo Dõi Pin Thiết Bị Không Dây",
            font=(font_family, 16, "bold"),
            bg=self.BG_HEADER,
            fg=self.FG_PRIMARY,
        ).pack(anchor="w")

        os_info = f"Hệ điều hành: {platform.system()} {platform.release()} ({platform.machine()})"
        self.subtitle_lbl = tk.Label(
            title_box,
            text=os_info,
            font=(font_family, 10),
            bg=self.BG_HEADER,
            fg=self.FG_SECONDARY,
        )
        self.subtitle_lbl.pack(anchor="w", pady=(2, 0))

        ctrl_box = tk.Frame(header, bg=self.BG_HEADER)
        ctrl_box.pack(side="right")

        self.scan_btn = tk.Button(
            ctrl_box,
            text="⟳ Quét ngay",
            command=self.trigger_scan,
            bg="#0284C7",
            fg="#FFFFFF",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            font=(font_family, 10, "bold"),
            cursor="hand2",
        )
        self.scan_btn.pack(side="left", padx=(0, 8))

        export_btn = tk.Button(
            ctrl_box,
            text="⬇ Xuất CSV",
            command=self.export_csv,
            bg="#334155",
            fg=self.FG_PRIMARY,
            activebackground="#475569",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=6,
            font=(font_family, 10),
            cursor="hand2",
        )
        export_btn.pack(side="left")

        # 2. Thanh tuỳ chọn (Auto-refresh, Always on top, Demo)
        toolbar = tk.Frame(self.root, bg=self.BG_MAIN, padx=18, pady=8)
        toolbar.pack(fill="x")

        tk.Label(
            toolbar,
            text="Tự động cập nhật:",
            bg=self.BG_MAIN,
            fg=self.FG_SECONDARY,
            font=(font_family, 10),
        ).pack(side="left")

        interval_menu = ttk.Combobox(
            toolbar,
            textvariable=self.interval_var,
            values=["Tắt", "10 giây", "30 giây", "60 giây", "5 phút"],
            state="readonly",
            width=10,
        )
        interval_menu.pack(side="left", padx=(6, 16))
        interval_menu.bind("<<ComboboxSelected>>", lambda _e: self._schedule_next_scan())

        tk.Checkbutton(
            toolbar,
            text="Ghim cửa sổ lên trên (Always on Top)",
            variable=self.topmost_var,
            command=self._toggle_topmost,
            bg=self.BG_MAIN,
            fg=self.FG_SECONDARY,
            selectcolor=self.BG_CARD,
            activebackground=self.BG_MAIN,
            activeforeground=self.FG_PRIMARY,
            font=(font_family, 10),
        ).pack(side="left", padx=(0, 16))

        tk.Checkbutton(
            toolbar,
            text="Hiển thị thiết bị mẫu nếu chưa kết nối",
            variable=self.demo_var,
            command=self.trigger_scan,
            bg=self.BG_MAIN,
            fg=self.FG_SECONDARY,
            selectcolor=self.BG_CARD,
            activebackground=self.BG_MAIN,
            activeforeground=self.FG_PRIMARY,
            font=(font_family, 10),
        ).pack(side="left")

        # 3. Các thẻ thống kê nhanh (Summary Cards)
        cards_frame = tk.Frame(self.root, bg=self.BG_MAIN, padx=18, pady=4)
        cards_frame.pack(fill="x")
        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)

        self.card_total = self._create_stat_card(cards_frame, 0, "Tổng thiết bị", "0", self.ACCENT_BLUE, font_family)
        self.card_avg = self._create_stat_card(cards_frame, 1, "Mức pin trung bình", "--%", self.COLOR_GOOD, font_family)
        self.card_lowest = self._create_stat_card(cards_frame, 2, "Thiết bị thấp nhất", "Chưa có", self.COLOR_WARN, font_family)
        self.card_alert = self._create_stat_card(cards_frame, 3, "Cần sạc (< 20%)", "0 thiết bị", self.COLOR_LOW, font_family)

        # 4. Danh sách thẻ trực quan có thanh mức pin + Bảng chi tiết
        content_frame = tk.Frame(self.root, bg=self.BG_MAIN, padx=18, pady=10)
        content_frame.pack(fill="both", expand=True)

        # Bảng Treeview hiển thị chuẩn xác từng cột
        cols = ("device", "category", "battery", "bar", "status", "protocol", "details")
        self.tree = ttk.Treeview(content_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("device", text="Tên thiết bị")
        self.tree.heading("category", text="Loại")
        self.tree.heading("battery", text="% Pin")
        self.tree.heading("bar", text="Biểu đồ mức pin")
        self.tree.heading("status", text="Trạng thái")
        self.tree.heading("protocol", text="Giao thức nhận diện")
        self.tree.heading("details", text="Chi tiết phụ (Trái/Phải/Hộp)")

        self.tree.column("device", width=220, anchor="w")
        self.tree.column("category", width=105, anchor="w")
        self.tree.column("battery", width=75, anchor="center")
        self.tree.column("bar", width=130, anchor="w")
        self.tree.column("status", width=95, anchor="center")
        self.tree.column("protocol", width=165, anchor="w")
        self.tree.column("details", width=190, anchor="w")

        self.tree.tag_configure("good", foreground="#4ADE80")
        self.tree.tag_configure("medium", foreground="#FBBF24")
        self.tree.tag_configure("low", foreground="#F87171")

        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 5. Thanh trạng thái dưới cùng
        footer = tk.Frame(self.root, bg=self.BG_HEADER, padx=18, pady=8)
        footer.pack(fill="x", side="bottom")

        self.status_lbl = tk.Label(
            footer,
            text="Đang khởi tạo trình quét đa giao thức...",
            bg=self.BG_HEADER,
            fg=self.FG_SECONDARY,
            font=(font_family, 9),
        )
        self.status_lbl.pack(side="left")

        self.proto_lbl = tk.Label(
            footer,
            text="",
            bg=self.BG_HEADER,
            fg=self.ACCENT_BLUE,
            font=(font_family, 9),
        )
        self.proto_lbl.pack(side="right")

    def _create_stat_card(
        self, parent: "tk.Frame", col: int, title: str, value: str, color: str, font_family: str
    ) -> "tk.Label":
        card = tk.Frame(parent, bg=self.BG_CARD, padx=14, pady=10, highlightthickness=1, highlightbackground="#334155")
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0 if col == 3 else 6))

        tk.Label(
            card,
            text=title,
            bg=self.BG_CARD,
            fg=self.FG_SECONDARY,
            font=(font_family, 9),
        ).pack(anchor="w")

        val_lbl = tk.Label(
            card,
            text=value,
            bg=self.BG_CARD,
            fg=color,
            font=(font_family, 14, "bold"),
        )
        val_lbl.pack(anchor="w", pady=(4, 0))
        return val_lbl

    def _toggle_topmost(self) -> None:
        self.root.attributes("-topmost", self.topmost_var.get())

    @staticmethod
    def _make_battery_bar(pct: int, width: int = 10) -> str:
        pct = max(0, min(100, pct))
        filled = round((pct / 100.0) * width)
        return "█" * filled + "░" * (width - filled)

    def trigger_scan(self) -> None:
        if self.is_scanning:
            return
        self.is_scanning = True
        self.scan_btn.configure(state="disabled", text="⏳ Đang quét...")
        self.status_lbl.configure(text="Đang quét các thiết bị không dây qua các giao thức hệ thống...")

        use_demo = self.demo_var.get()

        def worker() -> None:
            devs, protos = scan_all_wireless_devices(include_demo=use_demo)
            self.root.after(0, lambda: self._on_scan_done(devs, protos))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_done(self, devs: List[WirelessDevice], protos: List[str]) -> None:
        self.devices = devs
        self.protocols = protos
        self.is_scanning = False
        self.scan_btn.configure(state="normal", text="⟳ Quét ngay")

        # Xoá dữ liệu cũ
        for item in self.tree.get_children():
            self.tree.delete(item)

        for d in devs:
            bar_str = f"{self._make_battery_bar(d.battery)}  {d.battery}%"
            self.tree.insert(
                "",
                "end",
                values=(
                    f"{d.icon}  {d.name}",
                    d.category,
                    f"{d.battery}%",
                    bar_str,
                    d.status,
                    d.protocol,
                    d.details or "—",
                ),
                tags=(d.level_tag,),
            )

        # Cập nhật thẻ thống kê
        total = len(devs)
        self.card_total.configure(text=f"{total} thiết bị")
        if total > 0:
            avg_bat = sum(d.battery for d in devs) / total
            min_dev = min(devs, key=lambda x: x.battery)
            low_cnt = sum(1 for d in devs if d.battery < 20)
            self.card_avg.configure(text=f"{avg_bat:.1f}%")
            short_name = min_dev.name if len(min_dev.name) <= 18 else min_dev.name[:16] + "…"
            self.card_lowest.configure(text=f"{short_name} ({min_dev.battery}%)")
            self.card_alert.configure(text=f"{low_cnt} thiết bị ({low_cnt * 100 // total}%)")
        else:
            self.card_avg.configure(text="--%")
            self.card_lowest.configure(text="Không có")
            self.card_alert.configure(text="0 thiết bị")

        now_str = datetime.now().strftime("%H:%M:%S")
        if total == 0:
            self.status_lbl.configure(
                text=f"Cập nhật lúc {now_str} — Chưa phát hiện thiết bị không dây đang hoạt động (Tích 'Hiển thị thiết bị mẫu' để xem thử)."
            )
        else:
            self.status_lbl.configure(text=f"Cập nhật lúc {now_str} — Đã nhận diện {total} thiết bị không dây.")
        self.proto_lbl.configure(text="Giao thức: " + " • ".join(protos))

        self._schedule_next_scan()

    def _schedule_next_scan(self) -> None:
        if self.after_job is not None:
            try:
                self.root.after_cancel(self.after_job)
            except Exception:
                pass
            self.after_job = None

        mapping = {
            "10 giây": 10_000,
            "30 giây": 30_000,
            "60 giây": 60_000,
            "5 phút": 300_000,
        }
        ms = mapping.get(self.interval_var.get())
        if ms:
            self.after_job = self.root.after(ms, self.trigger_scan)

    def export_csv(self) -> None:
        if not self.devices:
            messagebox.showinfo("Xuất CSV", "Hiện chưa có dữ liệu thiết bị để xuất.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Lưu báo cáo pin thiết bị không dây",
            defaultextension=".csv",
            initialfile=f"wireless_battery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Tên thiết bị", "Loại", "Phần trăm pin (%)", "Trạng thái", "Giao thức", "Địa chỉ/ID", "Chi tiết"])
                for d in self.devices:
                    writer.writerow([d.name, d.category, d.battery, d.status, d.protocol, d.address, d.details])
            messagebox.showinfo("Thành công", f"Đã lưu báo cáo tại:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file CSV:\n{e}")


# ==============================================================================
# ĐIỂM KHỞI CHẠY CHÍNH (ENTRYPOINT)
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chương trình theo dõi % pin thiết bị không dây đa nền tảng (Windows, macOS, Linux)."
    )
    parser.add_argument("--cli", action="store_true", help="Chạy ở chế độ bảng thống kê trên Terminal (không mở GUI)")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả dạng JSON ra Terminal")
    parser.add_argument("--demo", action="store_true", help="Hiển thị dữ liệu thiết bị mẫu nếu máy chưa kết nối thiết bị")
    args = parser.parse_args()

    if args.json:
        devs, protos = scan_all_wireless_devices(include_demo=args.demo)
        payload = {
            "os": platform.system(),
            "timestamp": datetime.now().isoformat(),
            "protocols": protos,
            "devices": [asdict(d) for d in devs],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.cli or not HAS_TK or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")):
        devs, protos = scan_all_wireless_devices(include_demo=args.demo)
        print_cli_report(devs, protos)
        return

    root = tk.Tk()
    WirelessBatteryApp(root, start_with_demo=args.demo)
    root.mainloop()


if __name__ == "__main__":
    main()