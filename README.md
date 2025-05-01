# Hệ Thống Quản Lý Danh Mục Đầu Tư

- **Thành viên nhóm**
- **Thành viên 1**: Hoa Xuân Hoàn - 22689381
- **Thành viên 2**: Đào Tiến Sang - 22705971
- **Thành viên 3**: Nguyễn Chí Trung - 22719231
- **Thành viên 4**: Nguyễn Trường Vương - 22642961

## Giới Thiệu
Hệ thống quản lý danh mục đầu tư giúp người dùng theo dõi, mua bán tài sản tài chính và quản lý danh mục đầu tư của họ. Hệ thống cung cấp các chức năng như nạp tiền vào ví, giao dịch tài sản, theo dõi biến động thị trường, và báo cáo hiệu suất danh mục.

## Công Nghệ Sử Dụng
- **Font-End**: HTML, CSS, JavaScript
- **Back-End**: Django (Python)
- **Database**: PostgreSQL

## Các Tính Năng Chính
- Đăng ký, đăng nhập, xác thực người dùng
- Quản lý ví tiền, nạp tiền vào ví
- Tạo và quản lý danh mục đầu tư
- Mua, bán tài sản tài chính
- Theo dõi biến động giá thị trường
- Xem báo cáo hiệu suất danh mục đầu tư

## Cài đặt
Yêu cầu:
- PostgresSQL
- Python 3 trở lên

**- Windows:** Chạy file `run.bat` bằng cách click vào file \
**- Linux/MacOS:** Chạy file `run.sh` bằng cách chạy lệnh `bash run.sh` \
**- Docker:** Chạy trên các hệ điều hành \
    Chạy lệnh: `dos2unix entrypoint.sh` để chuyển định dạng file entrypoint.sh thành định dạng Unix \
    Chạy lệnh: `docker-compose up --build` để build các Image \
    Truy cập trình duyệt ở địa chỉ: http://localhost:8000/
