# 🔋 Theo dõi % Pin Thiết bị Không dây (Windows, macOS & Linux)

Công cụ nhỏ gọn, miễn phí giúp hiển thị chính xác phần trăm pin của các thiết bị không dây đang kết nối với máy tính của bạn (tai nghe Bluetooth, AirPods, chuột, bàn phím, tay cầm chơi game...).

> 💻 **Hỗ trợ đa nền tảng:** Chạy mượt mà trên cả **3 hệ điều hành phổ biến nhất hiện nay: Windows, macOS và Linux**.

---

## ✨ Tính năng nổi bật

1. **Chế độ dòng lệnh (`battery.py`):** 
   * Kiểm tra nhanh % pin tất cả thiết bị ngay trên màn hình dòng lệnh (Terminal / CMD).
   * **Không cần cài thêm bất kỳ thư viện nào**, chỉ cần có sẵn Python là chạy được ngay.
2. **Chế độ hiển thị icon trên thanh công cụ (`battery_tray.py`):** 
   * Hiện trực tiếp con số % pin lên thanh Menu (góc trên bên phải **macOS**) hoặc khay hệ thống (góc dưới bên phải **Windows / Linux**).
   * Icon tự đổi màu theo mức pin của thiết bị **yếu nhất**: 🟢 Xanh (> 50%), 🟠 Cam (21–50%), 🔴 Đỏ (≤ 20%).
   * Tự động cập nhật mỗi 60 giây và gửi thông báo nhắc sạc khi có thiết bị sắp hết pin (≤ 20%).

---

## 📋 Bước 1: Chuẩn bị trước khi dùng

### 1. Tải mã nguồn về máy
* Trên trang GitHub này, bấm vào nút màu xanh lá **`<> Code`** ở góc trên bên phải $\rightarrow$ chọn **`Download ZIP`**.
* Giải nén file `.zip` vừa tải về (bạn sẽ được một thư mục chứa 2 file là `battery.py` và `battery_tray.py`).

### 2. Đảm bảo máy đã cài Python 3
* **macOS:** Mở ứng dụng **Terminal** (bấm `Command + Space`, gõ `Terminal` rồi nhấn Enter) và gõ `python3 --version`. Nếu máy chưa có, một bảng thông báo sẽ hiện lên, bạn chỉ cần bấm **Install** (Cài đặt) là xong.
* **Windows:** Mở **Microsoft Store**, tìm từ khóa `Python 3.12` (hoặc bản mới nhất) và bấm **Get / Cài đặt**.
* **Linux:** Thường đã được cài đặt sẵn trong hệ thống.

---

## 📂 Bước 2: Mở Terminal và di chuyển vào thư mục chứa code

Để chạy được chương trình, bạn cần mở giao diện dòng lệnh và trỏ nó tới đúng thư mục vừa giải nén ở Bước 1.

1. **Mở cửa sổ dòng lệnh:**
   * **macOS / Linux:** Mở ứng dụng **Terminal**.
   * **Windows:** Bấm phím `Windows`, gõ `cmd` (hoặc `PowerShell`) rồi nhấn **Enter**.

2. **Làm quen 3 lệnh cơ bản (dành cho người chưa từng dùng dòng lệnh):**
   * `pwd` *(Print Working Directory)*: Gõ lệnh này và nhấn Enter để xem **bạn đang đứng ở thư mục nào** trên máy tính.
   * `cd` *(Change Directory)*: Dùng để **di chuyển** sang thư mục khác.
   * `ls` *(List)*: Dùng để **liệt kê** xem trong thư mục hiện tại đang có những file nào *(Lưu ý: trên Windows CMD thì dùng lệnh `dir` thay cho `ls`)*.

3. **Cách vào đúng thư mục chứa code nhanh nhất (Kéo & Thả):**
   * Tại cửa sổ Terminal/CMD, gõ chữ `cd ` *(lưu ý có **1 dấu cách** ở sau chữ `cd`, chưa nhấn Enter vội)*.
   * Mở Finder (macOS), File Explorer (Windows) hoặc Files (Linux), tìm đến thư mục vừa giải nén ở Bước 1.
   * Dùng chuột **kéo thả nguyên thư mục đó** vào thẳng bên trong cửa sổ Terminal/CMD. Đường dẫn thư mục sẽ tự động được điền vào!
   * Nhấn phím **Enter**.

4. **Kiểm tra lại cho chắc chắn:**
   * Gõ `pwd` rồi nhấn Enter $\rightarrow$ Bạn sẽ thấy đường dẫn hiện tại chính là thư mục vừa kéo vào.
   * Gõ `ls` *(hoặc `dir` trên Windows)* rồi nhấn Enter $\rightarrow$ Nếu thấy hiện tên 2 file `battery.py` và `battery_tray.py` là bạn đã làm đúng!

---

## 🚀 Bước 3: Chạy chương trình

### Cách 1: Xem nhanh trong Terminal (`battery.py`)
Cách này không cần cài đặt thêm bất kỳ thư viện nào. Tại cửa sổ Terminal ở Bước 2, bạn gõ một trong hai lệnh sau:

* **Xem 1 lần rồi thôi:**
  ```bash
  python3 battery.py
  ```
* **Tự động cập nhật liên tục mỗi 30 giây:**
  ```bash
  python3 battery.py --watch 30
  ```
  *(Muốn dừng lại thì nhấn tổ hợp phím `Ctrl + C`)*.

> **💡 Lưu ý cho người dùng Windows:** Nếu gõ `python3` mà báo lỗi không tìm thấy, bạn hãy đổi chữ `python3` thành `python` (ví dụ: `python battery.py`).

---

### Cách 2: Hiện icon % pin lên thanh công cụ (`battery_tray.py`)
Chế độ này giúp bạn theo dõi pin mọi lúc như một ứng dụng thực thụ.

1. **Cài đặt 2 thư viện hỗ trợ giao diện (chỉ cần làm 1 lần duy nhất):**
   Copy và dán lệnh sau vào Terminal rồi nhấn Enter:
   ```bash
   pip3 install pystray pillow
   ```
   *(Nếu dùng Windows và gặp lỗi với `pip3`, hãy thử dùng `pip install pystray pillow`)*.

2. **Chạy ứng dụng:**
   ```bash
   python3 battery_tray.py
   ```
   * Lúc này, hãy nhìn lên **thanh Menu trên cùng (macOS)** hoặc **khay hệ thống góc dưới bên phải (Windows / Linux - có thể nằm trong mũi tên `^`)**, bạn sẽ thấy một ô vuông nhỏ hiển thị con số % pin.
   * **Bấm vào icon đó** để xem chi tiết % pin từng thiết bị, bấm **Cập nhật ngay** hoặc **Thoát**.
   * *Lưu ý:* Không tắt cửa sổ Terminal đang chạy lệnh này (bạn có thể thu nhỏ nó xuống). Nếu tắt Terminal, icon trên thanh công cụ cũng sẽ tắt theo.

---

## ❓ Câu hỏi thường gặp (Xử lý lỗi)

* **Báo lỗi `No such file or directory` khi chạy lệnh:**
  Bạn đang đứng sai thư mục. Hãy thực hiện lại **Bước 2** (gõ `cd ` + kéo thả thư mục vào + Enter) rồi gõ `ls` để chắc chắn thấy file `battery.py`.
* **Báo lỗi `Thiếu thư viện` khi chạy `battery_tray.py`:**
  Bạn chưa cài thư viện giao diện. Hãy chạy lại lệnh `pip3 install pystray pillow`.
* **Chương trình báo *"Không đọc được pin của thiết bị nào"*:**
  1. Kiểm tra xem thiết bị không dây đã bật nguồn và kết nối Bluetooth/Receiver với máy tính chưa.
  2. Một số dòng chuột/bàn phím giá rẻ hoặc thiết bị dùng đầu thu USB riêng (2.4GHz) không gửi dữ liệu phần trăm pin cho hệ điều hành, nên máy tính không thể đọc được.
* **Trên macOS báo lỗi quyền hoặc không hiện thiết bị Bluetooth:**
  Vào **System Settings (Cài đặt hệ thống) $\rightarrow$ Privacy & Security (Quyền riêng tư & Bảo mật) $\rightarrow$ Bluetooth**, sau đó bật công tắc cho phép ứng dụng **Terminal** được truy cập Bluetooth.