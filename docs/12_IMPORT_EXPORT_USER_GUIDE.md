# TravelHub – Hướng dẫn sử dụng Import / Export Excel & CSV

> Phiên bản đầu tiên: áp dụng cho **danh mục Tour**, không áp dụng cho booking, thanh toán, hành khách hoặc dữ liệu CRM. Chức năng đang ở nhánh tính năng, chưa áp dụng lên môi trường production.

## 1. Ai được sử dụng?

- **ADMIN / SUPER_ADMIN**: xem, xuất danh sách, tải file mẫu, xem trước và nhập mới.
- **STAFF**: có quyền `tours:read` để xuất dữ liệu, nhưng không được nhập hoặc sửa tour.
- **CUSTOMER / khách chưa đăng nhập**: không được truy cập các API quản trị.

Phân quyền được kiểm tra ở backend; việc ẩn nút trên giao diện không thay thế phân quyền.

## 2. Mở công cụ ở đâu?

1. Đăng nhập vào **TravelHub Admin** tại `http://localhost:5174` (mặc định khi chạy local).
2. Mở **Tours**.
3. Tìm khung **Import / Export tours**.
4. Chọn `xlsx` (Excel) hoặc `csv` để tải mẫu hoặc xuất dữ liệu.

Nếu khung không xuất hiện, tài khoản không có quyền `tours:write`; STAFF hiện không thấy khung này dù có quyền API xuất dữ liệu.

## 3. Xuất danh sách Tour

1. Chọn định dạng **Excel (.xlsx)** hoặc **CSV (.csv)**.
2. Nhấn **Export tours**.
3. Lưu file về máy.

Xuất tất cả tour (bao gồm Draft/Published/Archived), **không chỉ trang đang hiển thị**, tối đa **10.000** bản ghi. File không chứa dữ liệu khách hàng, đặt chỗ hoặc thanh toán.

CSV dùng mã hóa **UTF-8 BOM**, thuận tiện để mở tiếng Việt trên Excel. XLSX mở bằng Excel hoặc LibreOffice.

### Các cột dữ liệu

| Cột | Ý nghĩa | Ví dụ |
| --- | --- | --- |
| `title` | Tên tour | Khám phá Đà Lạt |
| `slug` | Định danh URL duy nhất, chữ thường và dấu gạch ngang | `kham-pha-da-lat` |
| `description` | Mô tả, có thể để trống | Tour 3 ngày 2 đêm |
| `duration_days` | Số ngày (số nguyên dương) | `3` |
| `destination` | Điểm đến | Đà Lạt |

**Lưu ý:** File xuất không chứa trạng thái công khai. Mọi tour được nhập sẽ luôn là **Draft**, kể cả khi file xuất trước đó có tour Published.

## 4. Nhập dữ liệu

1. Nhấn **Download template** và chọn Excel hoặc CSV.
2. Điền dữ liệu đúng năm cột, giữ nguyên tên và thứ tự cột ở hàng đầu tiên.
3. Không thêm cột, không đổi tên cột và không thêm sheet trong Excel.
4. Lưu `.xlsx` hoặc `.csv`. Dung lượng file không vượt **2 MiB**.
5. Trong Admin → Tours, chọn file.
6. Nhấn **Preview import** để kiểm tra.
7. Đọc số dòng hợp lệ và danh sách lỗi (nếu có).
8. Sửa lỗi trên file rồi chọn lại file để xem trước lần nữa.
9. Khi **0 dòng lỗi**, nhấn **Import as drafts** và xác nhận.

Tối đa **500 dòng dữ liệu** cho mỗi lần nhập, không kể hàng tiêu đề.

### Ví dụ CSV

```csv
title,slug,description,duration_days,destination
Khám phá Đà Lạt,kham-pha-da-lat,Tham quan cao nguyên,3,Đà Lạt
Du lịch Hội An,du-lich-hoi-an,Khám phá phố cổ,2,Hội An
```

Nếu mô tả chứa dấu phẩy, hãy dùng dấu ngoặc kép CSV theo tiêu chuẩn.

## 5. Quy tắc an toàn

- **Chỉ tạo mới**: không cập nhật tour hiện có, không ghi đè dữ liệu cũ.
- **Không trùng slug**: trùng trong file hoặc trùng trong database sẽ báo lỗi.
- **Nguyên khối**: nếu có bất kỳ dòng không hợp lệ, **không tạo dòng nào**.
- **Bản nháp**: tour mới ở `draft`, không tự động xuất bản.
- **Không tạo Departure**: phải vào quản trị đợt khởi hành để bổ sung ngày, giá, tiền tệ và số chỗ.
- **Không động tới Booking hoặc Payment**.
- **Audit log**: mỗi tour được nhập có sự kiện `tour.bulk_imported` gắn tài khoản thao tác.
- Nếu người khác tạo tour trùng slug sau khi bạn xem trước, bước Import sẽ kiểm tra lại và có thể từ chối.

## 6. Các lỗi thường gặp

| Vấn đề | Cách xử lý |
| --- | --- |
| `Expected column order` | Tải file mẫu mới, giữ đúng thứ tự cột |
| `Slug already exists` | Đổi slug của tour nhập; bản đầu không có chế độ update |
| `Duplicate slug within uploaded file` | Mỗi dòng phải có slug khác nhau |
| `duration_days` không hợp lệ | Dùng số nguyên lớn hơn 0 |
| `Invalid or unreadable CSV/XLSX` | Lưu lại file đúng định dạng; CSV phải UTF-8 |
| `403 Forbidden` | Liên hệ Admin để kiểm tra quyền `tours:write` |
| `File must be between 1 byte and 2 MiB` | Chia file nhỏ hơn |
| `Import is limited to 500 data rows` | Tách thành nhiều file |
| Xuất trên 10.000 tour | Chưa hỗ trợ; cần thiết kế xuất dạng streaming hoặc chạy batch |

## 7. API tham khảo cho quản trị viên kỹ thuật

Cần JWT Bearer token có quyền tương ứng:

- `GET /api/v1/admin/tours/bulk/export?format=xlsx`
- `GET /api/v1/admin/tours/bulk/export?format=csv`
- `GET /api/v1/admin/tours/bulk/export?format=xlsx&template=true`
- `POST /api/v1/admin/tours/bulk/import?preview=true`, multipart `file`
- `POST /api/v1/admin/tours/bulk/import?preview=false`, multipart `file`

Phản hồi import có `preview`, `valid_rows`, `error_rows`, `errors` và `created`.

## 8. Chạy test trước khi merge

Từ môi trường có dependencies:

```bash
cd backend
pytest -q tests/test_catalog.py
cd ../frontend-admin
npm ci
npm test
npm run build
```

Sau đó chạy cả bộ Backend/Admin/User và kiểm tra migration, PostgreSQL concurrency qua môi trường test cách ly theo `README.md`.

**Chưa chạy xác nhận toàn bộ suite trong môi trường tạo nhánh. Không merge nếu test/build thất bại.**

## 9. Định hướng mở rộng

Những module có thể bổ sung tiếp theo: **Departures**, **Articles**, **Customers** (với bảo vệ dữ liệu cá nhân và quyền truy cập riêng), **Guides**, **Suppliers**. Booking/Payment chỉ nên cho phép xuất báo cáo đã kiểm soát; việc nhập/sửa giao dịch tài chính cần chính sách nghiệp vụ, audit, đối soát và phê duyệt riêng.

Tính năng Excel/CSV **không phụ thuộc ngôn ngữ giao diện**; có thể bổ sung tiếng Việt, Ý, Anh trong tương lai.
