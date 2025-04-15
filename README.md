# Hệ Thống Chia Sẻ Tệp P2P

Dự án này triển khai một hệ thống chia sẻ tệp ngang hàng (P2P) sử dụng tracker và các peer. Hệ thống hỗ trợ chia sẻ và tải xuống tệp bằng cách sử dụng các tệp metadata `.torrent`. 

## Tính Năng
- Chia sẻ tệp bằng cách tạo tệp `.torrent`.
- Tải xuống tệp từ các peer bằng cách sử dụng metadata `.torrent`.
- Hỗ trợ nhiều tệp và tải xuống đồng thời.

---

## Yêu Cầu
1. **Python 3.x** phải được cài đặt trên hệ thống của bạn.
2. Cài đặt các thư viện Python cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

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
Cài đặt này trong `config.py` định nghĩa kích thước tối đa của tệp torrent tính bằng kilobyte. Giá trị mặc định là `1024` (1 MB). Bạn có thể thay đổi giá trị này để điều chỉnh kích thước chunk tối đa cho việc chia sẻ tệp.

---

## Hướng Dẫn Sử Dụng

### Khởi Động Tracker
Chạy tracker trên máy chủ trung tâm với địa chỉ IP cục bộ (ví dụ: `192.168.1.100`) và một cổng cụ thể (ví dụ: `6881`):
```bash
python tracker.py --ip 192.168.1.100 --port 6881
```

### Khởi Động Peer
Chạy các peer trên các máy khác nhau trong mạng. Mỗi peer phải chỉ định địa chỉ IP của riêng nó và địa chỉ IP của tracker. Ví dụ:
```bash
python peer.py --ip 192.168.1.101 --port 6882 --tracker-ip 192.168.1.100 --tracker-port 6881
```

### Khởi Động GUI
Chạy GUI trên bất kỳ máy nào có một peer đang chạy:
```bash
python gui.py --peer-ip 192.168.1.101 --peer-port 6882
```
GUI sẽ kết nối với peer và cho phép bạn chia sẻ và tải xuống tệp.

---

## Sử Dụng GUI

### Bảng Tệp Đã Chia Sẻ
- **Thêm Tệp**: Nhấn nút "Add Files" để chọn các tệp để chia sẻ. Các tệp được chọn sẽ được đăng ký với tracker.

### Bảng Tệp Có Sẵn
- **Tải Xuống Đã Chọn**: Chọn một tệp từ danh sách và nhấn "Download Selected" để bắt đầu tải xuống tệp.

### Trình Quản Lý Tải Xuống
- Hiển thị tiến trình và trạng thái của các tệp đang tải xuống.

---