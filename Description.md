# Mô tả hệ thống chia sẻ file ngang hàng (P2P)

Hệ thống này được thiết kế để chia sẻ file giữa các peer thông qua một server trung gian (tracker). Dưới đây là các thành phần chính và cách hoạt động của hệ thống:

## 1. Thành phần chính

### **1.1 Tracker**
- **Vai trò:** 
  - Lưu trữ thông tin về các peer và các file mà chúng chia sẻ.
  - Cung cấp danh sách các peer có file được yêu cầu.
- **Chức năng chính:**
  - Đăng ký peer và file (`/register`).
  - Cung cấp danh sách các peer idle có file (`/get_n_file_idle_peers`).
  - Theo dõi trạng thái của các peer (`/heartbeat`).
  - Xóa các peer không hoạt động.

### **1.2 Peer**
- **Vai trò:** 
  - Chia sẻ file mà nó sở hữu.
  - Tải file từ các peer khác.
- **Chức năng chính:**
  - Đăng ký với tracker để thông báo file mà nó chia sẻ.
  - Yêu cầu danh sách các peer có file cần tải từ tracker.
  - Kết nối trực tiếp với các peer khác để tải file.
  - Gửi heartbeat để duy trì trạng thái hoạt động với tracker.

## 2. Quy trình hoạt động

### **2.1 Đăng ký thông tin peer và file**
- Peer gửi thông tin (IP, cổng, danh sách file) đến tracker qua endpoint `/register`.
- Tracker lưu thông tin peer và file vào cơ sở dữ liệu.

### **2.2 Yêu cầu danh sách các peer**
- Peer gửi yêu cầu đến tracker qua endpoint `/get_n_file_idle_peers` để lấy danh sách các peer có file cần tải.
- Tracker trả về danh sách các peer idle có file được yêu cầu.

### **2.3 Tải file từ peer**
- Peer kết nối trực tiếp với các peer trong danh sách nhận được từ tracker.
- Peer yêu cầu file hoặc các phần của file từ peer khác.
- File được tải theo chiến lược "Rarest-First" để tối ưu hóa việc phân phối.

### **2.4 Hoàn tất và cập nhật trạng thái**
- Sau khi tải xong file, peer thông báo hoàn tất với tracker qua endpoint `/complete_transfer`.
- Tracker cập nhật trạng thái của peer chia sẻ thành "idle".

## 3. Chiến lược "Rarest-First"
- Peer ưu tiên tải các phần file hiếm nhất (các phần có ít peer chia sẻ nhất).
- Điều này giúp tối ưu hóa việc phân phối file trong mạng.

## 4. Tính năng bổ sung
- **Xác minh tính toàn vẹn:** 
  - Sử dụng SHA-1 để kiểm tra tính toàn vẹn của file sau khi tải.
- **Xóa peer không hoạt động:** 
  - Tracker tự động xóa các peer không gửi heartbeat trong khoảng thời gian quy định.

## 5. Công nghệ sử dụng
- **Ngôn ngữ lập trình:** Python.
- **Thư viện:** Flask, asyncio, websockets, numpy, scipy.
- **Giao thức:** HTTP, WebSocket, TCP.

Hệ thống này giúp tối ưu hóa việc chia sẻ file trong mạng ngang hàng (P2P) và giảm tải cho tracker, vì dữ liệu được truyền trực tiếp giữa các peer.
