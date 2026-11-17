# 🔋 Wireless Battery Monitor — Trình Theo Dõi Pin Thiết Bị Không Dây Đa Nền Tảng

Công cụ đơn file Python (`wireless_battery_monitor.py`) giúp tự động nhận diện, phân loại và hiển thị chính xác phần trăm pin hiện tại của các thiết bị ngoại vi không dây (tai nghe, chuột, bàn phím, tay cầm chơi game, loa, bút cảm ứng/trackpad) trên cả **Windows**, **macOS** và **Linux**.

Chương trình được thiết kế theo triết lý **Zero-Dependency mặc định**: sử dụng trực tiếp thư viện chuẩn của Python (`tkinter`, `subprocess`, `ctypes`, `pathlib`, `json`, `csv`) kết hợp với các công cụ quản lý phần cứng có sẵn trên từng hệ điều hành, đồng thời tự động mở rộng sang các công cụ chuyên biệt (như `solaar`, `upower`, `bluetoothctl`) khi phát hiện có trên máy.

## 1. Tính năng nổi bật

* **Đa nền tảng trong 1 file duy nhất:** Chạy trực tiếp trên Windows 10/11, macOS (Intel & Apple Silicon M-series) và các bản phân phối Linux phổ biến (Ubuntu, Debian, Fedora, Arch...).
* **Quét đa giao thức & Khử trùng lặp thông minh:** Tự động gộp thông tin từ nhiều tầng giao thức (Bluetooth Classic HFP, BLE GATT `0x180F`, Apple HID/IORegistry, USB 2.4GHz HID++, Windows PnP/WMI, XInput DLL, Linux Kernel `sysfs`) dựa trên địa chỉ MAC/Serial để không hiển thị trùng thiết bị.
* **Hỗ trợ chi tiết từng thành phần pin:** Hiển thị tách biệt phần trăm pin **Tai trái / Tai phải / Hộp sạc** đối với các dòng tai nghe True Wireless (như AirPods, Beats) trên macOS.
* **Tự động phân loại thiết bị kèm biểu tượng:** Nhận diện tự động 🎧 Tai nghe, 🖱️ Chuột, ⌨️ Bàn phím, 🎮 Tay cầm, 🔊 Loa, ✒️ Bút / Trackpad.
* **Giao diện GUI trực quan & Không gây đơ máy:** Quét thiết bị trên luồng nền (`threading.Thread`), hỗ trợ tự động làm mới định kỳ (10 giây, 30 giây, 60 giây, 5 phút), ghim cửa sổ lên trên cùng (**Always on Top**) và xuất báo cáo ra file **CSV** (UTF-8 có BOM, mở trực tiếp bằng Excel không lỗi tiếng Việt).
* **Hỗ trợ chế độ Terminal CLI & JSON:** Tự động chuyển sang in bảng thống kê kèm phần trăm khi chạy trên môi trường không có màn hình đồ hoạ hoặc khi gọi qua tham số dòng lệnh.

## 2. Yêu cầu hệ thống

Chương trình yêu cầu **Python 3.8 trở lên**. Hầu hết các bộ cài Python chính thức trên Windows và macOS đã tích hợp sẵn thư viện giao diện `tkinter`.

| Hệ điều hành | Yêu cầu mặc định | Lệnh cài đặt bổ sung (nếu thiếu giao diện `tkinter` hoặc công cụ phụ trợ) |
| :--- | :--- | :--- |
| **Windows 10 / 11** | Python 3.8+, PowerShell (có sẵn) | Tích chọn `tcl/tk and IDLE` khi cài Python từ python.org |
| **macOS** | Python 3.8+, `ioreg`, `system_profiler`, `pmset` (có sẵn) | Nếu dùng Homebrew Python: `brew install python-tk` |
| **Linux (Ubuntu/Debian)** | Python 3.8+, Kernel `sysfs` (có sẵn) | `sudo apt install python3-tk upower bluez solaar` |
| **Linux (Fedora)** | Python 3.8+, Kernel `sysfs` (có sẵn) | `sudo dnf install python3-tkinter upower bluez solaar` |
| **Linux (Arch)** | Python 3.8+, Kernel `sysfs` (có sẵn) | `sudo pacman -S tk upower bluez-utils solaar` |

## 3. Hướng dẫn khởi chạy

Mở **Terminal** (trên macOS/Linux) hoặc **PowerShell / Command Prompt** (trên Windows) tại thư mục chứa file `wireless_battery_monitor.py` và chạy một trong các lệnh sau:

### Khởi chạy giao diện đồ hoạ (GUI — Mặc định)

```bash
python3 wireless_battery_monitor.py
```

*(Trên Windows có thể dùng `python wireless_battery_monitor.py` hoặc `py wireless_battery_monitor.py`).*

### Khởi chạy kèm dữ liệu mẫu (Chế độ Demo)

Dùng khi bạn muốn kiểm tra thử bố cục giao diện, màu sắc cảnh báo pin và chức năng xuất CSV ngay cả khi chưa bật thiết bị không dây:

```bash
python3 wireless_battery_monitor.py --demo
```

### Khởi chạy chế độ bảng thống kê trên Terminal (CLI)

In trực tiếp bảng danh sách thiết bị, phần trăm pin từng thiết bị và dòng tổng hợp thống kê (tổng số thiết bị, mức pin trung bình, tỷ lệ thiết bị pin yếu `< 20%`, thiết bị thấp nhất/cao nhất) ngay trên cửa sổ dòng lệnh:

```bash
python3 wireless_battery_monitor.py --cli
```

Hoặc xem bảng CLI với dữ liệu mẫu:

```bash
python3 wireless_battery_monitor.py --cli --demo
```

### Xuất dữ liệu chuẩn JSON (Phục vụ tích hợp script / tự động hoá)

```bash
python3 wireless_battery_monitor.py --json
```

## 4. Các giao thức nhận diện pin theo từng hệ điều hành

Chương trình tự động phát hiện hệ điều hành đang chạy và kích hoạt toàn bộ các bộ quét tương thích:

| Hệ điều hành | Giao thức / Nguồn dữ liệu | Thiết bị tiêu biểu được hỗ trợ |
| :--- | :--- | :--- |
| **macOS** | `ioreg -r -l -w 0` (Apple IORegistry) | Magic Mouse, Magic Keyboard, Magic Trackpad, AirPods / Beats (báo riêng Trái/Phải/Hộp), chuột/phím BLE & USB 2.4GHz HID |
| **macOS** | `system_profiler SPBluetoothDataType -json` | Tai nghe Bluetooth Classic, loa Bluetooth, tay cầm DualSense/Xbox, chuột/phím hãng thứ ba |
| **macOS** | `pmset -g accps` (Power Management) | Các phụ kiện không dây đăng ký nguồn với macOS Power Management |
| **Windows** | PnP `DEVPKEY` (`{104EA319-...} 2`) | Chuột, bàn phím, tai nghe, bút cảm ứng dùng chuẩn Bluetooth Low Energy (BLE GATT `0x180F`) và HID Battery |
| **Windows** | PnP `DEVPKEY` (`{F0E20F09-...} 2`) | Tai nghe và loa Bluetooth Classic báo pin qua giao thức rảnh tay Hands-Free Profile (HFP) |
| **Windows** | WMI / CIM `Win32_Battery` | Thiết bị ngoại vi HID không dây và đầu thu USB báo cáo qua lớp WMI Battery (tự động lọc bỏ pin trong của Laptop) |
| **Windows** | Native DLL `XInputGetBatteryInformation` | Tay cầm Xbox Wireless (qua cả đầu thu USB 2.4GHz Xbox Wireless Adapter và Bluetooth) cùng các tay cầm chuẩn XInput |
| **Linux** | Kernel `/sys/class/power_supply/` | Chuột/phím Logitech HID++ (Unifying, Bolt, Lightspeed), tay cầm Sony DualSense/DualShock, thiết bị BLE & HID |
| **Linux** | `upower -d` (UPower Daemon) | Tất cả thiết bị ngoại vi không dây được Desktop Environment quản lý nguồn |
| **Linux** | `bluetoothctl` (BlueZ Stack) | Tai nghe Bluetooth HFP (`AT+IPHONEACCEV` / `AT+BIEV`) và thiết bị BLE GATT |
| **Đa nền tảng** | `solaar show` (Logitech HID++) | Chuột và bàn phím Logitech kết nối qua đầu thu USB 2.4GHz Unifying, Bolt, Lightspeed (khi máy có cài Solaar) |

## 5. Hướng dẫn sử dụng giao diện GUI

Trên cửa sổ chính của chương trình:

* **Nút `⟳ Quét ngay`:** Kích hoạt quét lại toàn bộ các giao thức ngay lập tức.
* **Nút `⬇ Xuất CSV`:** Lưu bảng trạng thái pin hiện tại ra file `.csv` kèm dấu thời gian (ví dụ: `wireless_battery_20261118_023500.csv`).
* **Menu `Tự động cập nhật`:** Chọn chu kỳ tự động quét ngầm (`Tắt`, `10 giây`, `30 giây`, `60 giây`, `5 phút`).
* **Ô tích `Ghim cửa sổ lên trên (Always on Top)`:** Giữ cửa sổ luôn nổi trên các ứng dụng khác để tiện theo dõi khi đang làm việc hoặc chơi game.
* **Ô tích `Hiển thị thiết bị mẫu nếu chưa kết nối`:** Tự động nạp 4 thiết bị mẫu khi máy không có thiết bị không dây nào đang bật.
* **Mã màu cảnh báo trực quan:**
  * **Màu xanh lá (`>= 50%`):** Pin tốt.
  * **Màu vàng cam (`20% – 49%`):** Pin trung bình.
  * **Màu đỏ (`< 20%`):** Cảnh báo pin yếu, cần sạc sớm (được tổng hợp riêng tại thẻ **Cần sạc (< 20%)** ở đầu cửa sổ).

## 6. Đóng gói thành file chạy độc lập (Tuỳ chọn)

Nếu bạn muốn đóng gói `wireless_battery_monitor.py` thành một file thực thi duy nhất (`.exe` trên Windows, `.app` trên macOS, hoặc binary trên Linux) để chạy trên máy không cài Python:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "WirelessBatteryMonitor" wireless_battery_monitor.py
```

File hoàn chỉnh sau khi đóng gói sẽ nằm trong thư mục `dist/`.

## 7. Xử lý sự cố thường gặp (Troubleshooting)

* **Thiết bị đã kết nối nhưng chưa hiển thị phần trăm pin:**
  * Một số chuột, bàn phím hoặc tay cầm chuyển sang chế độ ngủ (Sleep) sau vài phút không tương tác; hãy di chuột hoặc bấm một phím bất kỳ trên thiết bị rồi nhấn **`⟳ Quét ngay`**.
  * Một số mẫu tai nghe Bluetooth giá rẻ chỉ gửi bản tin báo pin ngay thời điểm vừa kết nối; hãy thử tắt/bật lại Bluetooth nếu hệ điều hành chưa kịp ghi nhận thuộc tính pin.
* **Thiết bị dùng đầu thu USB 2.4GHz (Logitech, Razer, Pulsar...):**
  * Trên **Linux**, kernel hiện đại tự động nhận diện hầu hết đầu thu Logitech qua driver `hid-logitech-hidpp` trong `/sys/class/power_supply/`; bạn có thể cài thêm `solaar` để đọc chi tiết hơn.
  * Trên **Windows** và **macOS**, các đầu thu USB 2.4GHz sử dụng giao thức HID chuẩn sẽ tự động xuất hiện trong WMI/IORegistry; với các dòng gaming khoá giao thức độc quyền (chỉ đọc được qua gói tin USB HID thô theo Vendor ID / Product ID riêng), bạn có thể bổ sung module đọc `hidapi` tương ứng với mã `VID:PID` của thiết bị.
