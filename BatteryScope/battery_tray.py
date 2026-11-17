#!/usr/bin/env python3
"""
Icon %pin trên thanh menu (macOS) / khay hệ thống (Windows, Linux).

- Icon hiện % pin của thiết bị YẾU NHẤT (xanh > 50%, cam 21-50%, đỏ <= 20%).
- Bấm vào icon để xem danh sách tất cả thiết bị.
- Tự cập nhật mỗi 60 giây, báo khi pin <= 20%.

Cần: battery.py nằm CÙNG THƯ MỤC với file này, và cài thư viện:
    pip3 install pystray pillow
Chạy:
    python3 battery_tray.py
"""
import platform
import subprocess
import sys
import threading
import time
import traceback

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Thiếu thư viện. Hãy chạy lệnh:  pip3 install pystray pillow")
    sys.exit(1)

try:
    from battery import collect
except ImportError:
    print("Không tìm thấy battery.py. Hãy để battery.py cùng thư mục với file này.")
    sys.exit(1)

SYSTEM = platform.system()
REFRESH_SECONDS = 60
LOW = 20          # báo khi pin <= mức này
RECOVER = 25      # pin lên trên mức này thì lần sau lại báo được

devices = []      # [(tên, %, nguồn)]
notified = set()  # thiết bị đã báo pin yếu
lock = threading.Lock()
refresh_lock = threading.Lock()
stop_event = threading.Event()
first_done = False  # đã đọc xong lần đầu chưa


# ---------------------------- Vẽ icon ----------------------------
def get_font(size):
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        pass
    for name in ("Arial.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_icon(pct):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if pct is None:
        color, text = (120, 120, 120, 255), "?"
    else:
        text = str(pct)
        if pct <= LOW:
            color = (220, 53, 69, 255)
        elif pct <= 50:
            color = (240, 150, 20, 255)
        else:
            color = (40, 167, 69, 255)
    d.rounded_rectangle((2, 8, size - 2, size - 8), radius=12, fill=color)
    font = get_font(26 if len(text) >= 3 else 36)
    box = d.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((size - w) / 2 - box[0], (size - h) / 2 - box[1]), text, font=font, fill="white")
    return img


# ---------------------------- Thông báo ----------------------------
def notify(icon, title, msg):
    title = title.replace('"', "'")
    msg = msg.replace('"', "'")
    try:
        if SYSTEM == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'display notification "{msg}" with title "{title}"'],
                timeout=10,
            )
        else:
            icon.notify(msg, title)
    except Exception:
        pass


def check_low_battery(icon, devs):
    for name, pct, _ in devs:
        if pct <= LOW and name not in notified:
            notified.add(name)
            notify(icon, "Pin yếu", f"{name} còn {pct}%")
        elif pct > RECOVER:
            notified.discard(name)


# ---------------------------- Menu & cập nhật ----------------------------
def menu_items():
    with lock:
        devs = list(devices)
    if not devs:
        text = "Chưa đọc được thiết bị nào" if first_done else "Đang đọc dữ liệu..."
        yield pystray.MenuItem(text, lambda i, m: None, enabled=False)
    for name, pct, _ in sorted(devs, key=lambda x: x[1]):
        warn = "  ⚠" if pct <= LOW else ""
        yield pystray.MenuItem(f"{name}: {pct}%{warn}", lambda i, m: None, enabled=False)
    yield pystray.Menu.SEPARATOR
    yield pystray.MenuItem("Cập nhật ngay", lambda icon, item: threading.Thread(
        target=refresh, args=(icon,), daemon=True).start())
    yield pystray.MenuItem("Thoát", lambda icon, item: (stop_event.set(), icon.stop()))


def refresh(icon):
    if not refresh_lock.acquire(blocking=False):
        return  # đang cập nhật rồi
    try:
        global first_done
        try:
            devs = collect()
        except Exception:
            traceback.print_exc()
            devs = []
        first_done = True
        print(f"[{time.strftime('%H:%M:%S')}] đọc được {len(devs)} thiết bị: {devs}", flush=True)
        with lock:
            devices[:] = devs
        lowest = min((p for _, p, _ in devs), default=None)
        try:
            icon.icon = make_icon(lowest)
            icon.title = "Pin thiết bị: " + (
                ", ".join(f"{n} {p}%" for n, p, _ in devs) if devs else "không có dữ liệu"
            )
            icon.update_menu()
            check_low_battery(icon, devs)
        except Exception:
            traceback.print_exc()
    finally:
        refresh_lock.release()


def loop(icon):
    icon.visible = True
    while not stop_event.is_set():
        refresh(icon)
        stop_event.wait(REFRESH_SECONDS)


def main():
    icon = pystray.Icon("battery", make_icon(None), "Pin thiết bị", pystray.Menu(menu_items))
    icon.run(setup=lambda ic: threading.Thread(target=loop, args=(ic,), daemon=True).start())


if __name__ == "__main__":
    main()
