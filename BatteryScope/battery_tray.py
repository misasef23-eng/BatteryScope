#!/usr/bin/env python3
"""
Icon %pin trên thanh menu (macOS) / khay hệ thống (Windows, Linux).

- Icon hiện % pin của thiết bị YẾU NHẤT (xanh > 50%, cam 21-50%, đỏ <= 20%).
- Bấm vào icon để xem danh sách tất cả thiết bị.
- Tự cập nhật mỗi 60 giây (8 giây nếu chưa thấy thiết bị nào, và đọc ngay khi máy thức dậy), báo khi pin <= 20%.

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
REFRESH_SECONDS = 60   # chu kỳ cập nhật khi đang có thiết bị
RETRY_SECONDS = 8      # chu kỳ khi chưa thấy thiết bị nào (để bắt nhanh lúc vừa kết nối)
TICK = 2               # nhịp kiểm tra (giây), dùng để phát hiện máy vừa thức dậy
LOW = 20          # báo khi pin <= mức này
RECOVER = 25      # pin lên trên mức này thì lần sau lại báo được

devices = []      # [(tên, %, nguồn)]
notified = set()  # thiết bị đã báo pin yếu
lock = threading.Lock()
refresh_lock = threading.Lock()
stop_event = threading.Event()
first_done = False  # đã đọc xong lần đầu chưa


# ---------------------------- Vẽ icon ----------------------------
BOLD_FONTS = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",   # macOS
    "/System/Library/Fonts/Helvetica.ttc",                  # macOS
    "arialbd.ttf",                                          # Windows
    "DejaVuSans-Bold.ttf",                                  # Linux
    "Arial Bold.ttf",
)


def get_font(size):
    for path in BOLD_FONTS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def make_icon(pct):
    """Vẽ icon ở độ phân giải cao (512px) rồi thu nhỏ để chữ sắc nét."""
    big, out = 512, 128
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if pct is None:
        color, text = (110, 110, 110, 255), "?"
    else:
        text = str(pct)
        if pct <= LOW:
            color = (215, 40, 50, 255)
        elif pct <= 50:
            color = (225, 120, 0, 255)
        else:
            color = (30, 150, 60, 255)
    d.rounded_rectangle((16, 16, big - 16, big - 16), radius=110, fill=color)

    # chọn cỡ chữ lớn nhất mà vẫn vừa khung
    max_w, max_h = big * 0.82, big * 0.62
    size = 400
    while size > 40:
        font = get_font(size)
        box = d.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_w and box[3] - box[1] <= max_h:
            break
        size -= 8
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((big - w) / 2 - box[0], (big - h) / 2 - box[1]), text, font=font, fill="white")
    return img.resize((out, out), Image.LANCZOS)


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
        with lock:
            empty = not devices
        interval = RETRY_SECONDS if empty else REFRESH_SECONDS
        waited = 0
        last = time.time()
        while waited < interval and not stop_event.is_set():
            stop_event.wait(TICK)
            now = time.time()
            if now - last > TICK * 4:  # đồng hồ nhảy vọt = máy vừa thức dậy sau khi ngủ
                stop_event.wait(4)     # chờ Bluetooth kết nối lại rồi đọc ngay
                break
            last = now
            waited += TICK


def main():
    icon = pystray.Icon("battery", make_icon(None), "Pin thiết bị", pystray.Menu(menu_items))
    icon.run(setup=lambda ic: threading.Thread(target=loop, args=(ic,), daemon=True).start())


if __name__ == "__main__":
    main()
