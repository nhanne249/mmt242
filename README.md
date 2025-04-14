# Hệ Thống Chia Sẻ Tệp P2P

Dự án này triển khai một hệ thống chia sẻ tệp ngang hàng (P2P) sử dụng tracker và các peer. Hệ thống hỗ trợ chia sẻ và tải xuống tệp bằng cách sử dụng các tệp metadata `.torrent`. Nó có thể chạy trên localhost hoặc trên các địa chỉ IP khác nhau trong cùng một mạng.

## Tính Năng
- Chia sẻ tệp bằng cách tạo tệp `.torrent`.
- Tải xuống tệp từ các peer bằng cách sử dụng metadata `.torrent`.
- Hỗ trợ nhiều tệp và tải xuống đồng thời.
- Hoạt động trên cả localhost và các địa chỉ IP khác nhau trong mạng.

---

## Yêu Cầu
1. **Python 3.x** phải được cài đặt trên hệ thống của bạn.
2. Cài đặt các thư viện Python cần thiết (nếu có):
   ```bash
   pip install -r requirements.txt
   ```
   Nếu không có `requirements.txt`, hãy đảm bảo bạn đã cài đặt các thư viện sau:
   - `PyQt5` (cho giao diện đồ họa GUI)

---

## Mô Tả Các Tệp

### `peer.py`
Xử lý các hoạt động của peer như đăng ký tệp, tải xuống tệp và giao tiếp với tracker và các peer khác.

### `tracker.py`
Hoạt động như một máy chủ trung tâm để quản lý metadata tệp và thông tin của các peer.

### `torrent.py`
Cung cấp các tiện ích để tạo và phân tích tệp `.torrent`.

### `network.py`
Chứa các hàm hỗ trợ cho giao tiếp socket, như gửi và nhận dữ liệu.

### `gui.py`
Triển khai giao diện đồ họa (GUI) để tương tác với hệ thống P2P.

### `config.py`
Chứa các cài đặt cấu hình, chẳng hạn như `TORRENT_MAX_SIZE_KB`, định nghĩa kích thước tối đa của tệp torrent tính bằng kilobyte.

---

## Cấu Hình

### `TORRENT_MAX_SIZE_KB`
Cài đặt này trong `config.py` định nghĩa kích thước tối đa của tệp torrent tính bằng kilobyte. Giá trị mặc định là `512`. Bạn có thể thay đổi giá trị này để điều chỉnh kích thước chunk tối đa cho việc chia sẻ tệp.

---

## Chạy Hệ Thống

### Trường Hợp 1: Chạy Trên Localhost
Trong trường hợp này, tất cả các thành phần (tracker và peer) sẽ chạy trên cùng một máy sử dụng `127.0.0.x` (localhost).

#### Bước 1: Khởi Động Tracker
Chạy tracker trên `127.0.0.1` với một cổng cụ thể (ví dụ: `6881`):
```bash
python tracker.py --ip 127.0.0.1 --port 6881
```

#### Bước 2: Khởi Động Peer
Chạy một hoặc nhiều peer trên `127.0.0.x` với các cổng khác nhau. Ví dụ:
```bash
python peer.py --ip 127.0.0.2 --port 6882 --tracker-ip 127.0.0.1 --tracker-port 6881
```
Bạn có thể chạy nhiều peer bằng cách sử dụng các giá trị `--ip` và `--port` khác nhau (ví dụ: `127.0.0.3`, `6883`, v.v.).

#### Bước 3: Khởi Động GUI
Chạy GUI để tương tác với hệ thống:
```bash
python gui.py
```
GUI sẽ kết nối với một peer và cho phép bạn chia sẻ và tải xuống tệp.

---

### Trường Hợp 2: Chạy Trên Các Địa Chỉ IP Khác Nhau
Trong trường hợp này, tracker và các peer sẽ chạy trên các máy khác nhau trong cùng một mạng (ví dụ: Wi-Fi hoặc LAN).

#### Bước 1: Khởi Động Tracker
Chạy tracker trên máy sẽ hoạt động như máy chủ trung tâm. Sử dụng địa chỉ IP cục bộ của máy (ví dụ: `192.168.1.100`):
```bash
python tracker.py --ip 192.168.1.100 --port 6881
```

#### Bước 2: Khởi Động Peer
Chạy các peer trên các máy khác nhau trong mạng. Mỗi peer phải chỉ định địa chỉ IP của riêng nó và địa chỉ IP của tracker. Ví dụ:
```bash
python peer.py --ip 192.168.1.101 --port 6882 --tracker-ip 192.168.1.100 --tracker-port 6881
```
Bạn có thể chạy nhiều peer trên các máy khác nhau hoặc trên cùng một máy (sử dụng các cổng khác nhau).

#### Bước 3: Khởi Động GUI
Chạy GUI trên bất kỳ máy nào có một peer đang chạy:
```bash
python gui.py
```
GUI sẽ kết nối với peer và cho phép bạn chia sẻ và tải xuống tệp.

---

## Sử Dụng GUI

### Bảng Tệp Đã Chia Sẻ
- **Thêm Tệp**: Nhấn nút "Add Files" để chọn các tệp để chia sẻ. Các tệp được chọn sẽ được đăng ký với tracker.

### Bảng Tệp Có Sẵn
- **Tải Xuống Đã Chọn**: Chọn một tệp từ danh sách và nhấn "Download Selected" để bắt đầu tải xuống tệp. Hệ thống sẽ tự động lấy tệp `.torrent` và tải tệp xuống theo từng phần.

### Trình Quản Lý Tải Xuống
- Hiển thị tiến trình của các tệp đang tải xuống.
- Hiển thị trạng thái của từng tệp (ví dụ: đang tải xuống, đã hoàn thành).

### Bảng Cài Đặt
- Nhập IP và cổng của tracker để kết nối với tracker.

---

## Logging
Hệ thống sử dụng module `logging` của Python để ghi lại các sự kiện và lỗi quan trọng. Các log được hiển thị trong console và có thể được sử dụng để debug.

---

## Quy Trình Ví Dụ
1. Khởi động tracker trên `192.168.1.100` (hoặc `127.0.0.1` cho localhost).
2. Khởi động Peer A trên `192.168.1.101` (hoặc `127.0.0.2` cho localhost) và chia sẻ một tệp.
3. Khởi động Peer B trên `192.168.1.102` (hoặc `127.0.0.3` cho localhost) và tải xuống tệp được chia sẻ bởi Peer A.
4. Sử dụng GUI để quản lý việc chia sẻ và tải xuống tệp.

---

## Xử Lý Sự Cố
- **Không thể kết nối với tracker:** Đảm bảo tracker đang chạy và IP/cổng là chính xác.
- **Các peer không tìm thấy nhau:** Đảm bảo tất cả các peer đang sử dụng cùng một IP và cổng của tracker.
- **Vấn đề tường lửa:** Cho phép Python qua tường lửa hoặc tạm thời tắt tường lửa để kiểm tra.

---

Chúc bạn sử dụng Hệ Thống Chia Sẻ Tệp P2P vui vẻ!
