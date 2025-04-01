# Bài Tập Lớn Mạng Máy Tính

## Cách Cài Đặt Các Thư Viện Yêu Cầu
Trước khi chạy chương trình, hãy đảm bảo rằng bạn đã cài đặt đầy đủ các thư viện yêu cầu. Sử dụng lệnh sau để cài đặt:
```bash
pip install -r requirements.txt
```
Lệnh này sẽ tự động cài đặt tất cả các thư viện cần thiết được liệt kê trong file `requirements.txt`.

## Cách Chạy Server
Để khởi động server, sử dụng lệnh sau:
```bash
python start_tracker
```
Lệnh này khởi tạo server tracker, quản lý việc đăng ký các PEER và hỗ trợ chia sẻ file giữa chúng.

## Cách Đăng Ký PEER Kèm File Đến Server
Để đăng ký một PEER cùng với các file mà nó muốn chia sẻ, sử dụng lệnh sau:
```bash
python start_client.py --port 1109 --files fileA1.txt fileA2.txt --peer_name "PEER A"
```
- `--port 1109`: Chỉ định số cổng mà PEER sẽ sử dụng.
- `--files fileA1.txt fileA2.txt`: Liệt kê các file mà PEER muốn chia sẻ.
- `--peer_name "PEER A"`: Gán tên cho PEER để nhận diện.

## Cách Một PEER Lấy File Từ PEER Khác Qua Server
Để yêu cầu file từ một PEER khác đang chia sẻ, sử dụng lệnh sau:
```bash
python start_client.py --port 1110 --peer_name "PEER B" --request_files fileA1.txt
```
- `--port 1110`: Chỉ định số cổng mà PEER yêu cầu sẽ sử dụng.
- `--peer_name "PEER B"`: Gán tên cho PEER yêu cầu.
- `--request_files fileA1.txt`: Chỉ định file mà PEER muốn lấy.

Hãy đảm bảo rằng server tracker đang chạy và PEER chia sẻ file được yêu cầu đã đăng ký với server trước khi thực hiện yêu cầu.
