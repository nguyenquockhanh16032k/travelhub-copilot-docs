# TRAVELHUB – SỔ TAY SỬ DỤNG HỆ THỐNG

**Phiên bản tài liệu:** 24/11/2026 · **Môi trường:** Development / Local. Các tính năng dưới đây dựa trên module đang có trong source; không đồng nghĩa dự án đã được kiểm thử end-to-end hoặc triển khai production.

## 1. Giới thiệu

TravelHub gồm ba thành phần:

| Thành phần | URL mặc định khi chạy local | Mục đích |
| --- | --- | --- |
| Website khách hàng | `http://localhost:5173` | Xem tour, tìm kiếm, đặt tour, đăng nhập xem lịch sử |
| Admin | `http://localhost:5174` | Quản lý tour, booking, khách hàng, thanh toán và vận hành |
| FastAPI Swagger | `http://localhost:8000/docs` | Xem và kiểm tra API kỹ thuật |

Phần mềm hiện **chưa có** cổng thanh toán thật, tự động hoàn tiền, đăng ký khách hàng công khai, quên mật khẩu, đa ngôn ngữ hay upload hình ảnh tour.

## 2. Đăng nhập và phân quyền

- **SUPER_ADMIN:** quản trị hệ thống và phân quyền theo chính sách hiện tại.
- **ADMIN:** quản trị kinh doanh, tour, departure, khách hàng, booking, thanh toán và nội dung; không tự cấp SUPER_ADMIN.
- **STAFF:** xem tour/departure; làm nghiệp vụ booking và khách hàng; chỉ đọc các thông tin vận hành được phép; không quản trị thanh toán/báo cáo tài chính.
- **CUSTOMER:** đăng nhập website User và xem booking của hồ sơ gắn với tài khoản mình.
- **Guest:** có thể xem tour và tạo yêu cầu booking mà không cần tài khoản.

**Không dùng chung tài khoản** giữa nhiều nhân viên. Quyền thực tế do FastAPI kiểm tra, không phải do việc hiển thị nút trên giao diện.

## 3. Quy trình vận hành thường ngày (Admin)

### Bước 1 – Tạo và công bố Tour

1. Vào Admin → **Tours**.
2. Nhấn **Create tour**.
3. Nhập tên, slug, điểm đến, số ngày và mô tả.
4. Lưu ở `draft` để kiểm tra nội dung.
5. Khi thông tin đúng, người có quyền mới chỉnh status thành `published`.

Tour là sản phẩm tái sử dụng; việc công bố Tour **không tự tạo** ngày khởi hành, giá hoặc số chỗ.

**Nhập/xuất hàng loạt Excel/CSV:** xem [12_IMPORT_EXPORT_USER_GUIDE.md](./12_IMPORT_EXPORT_USER_GUIDE.md). Chức năng này hiện nằm trong PR chờ kiểm thử.

### Bước 2 – Tạo đợt khởi hành (Departure)

1. Vào **Departures**, tạo departure gắn với một Tour đã tồn tại.
2. Khai báo ngày bắt đầu/kết thúc, sức chứa, giá, tiền tệ và trạng thái.
3. Chỉ những departure đủ điều kiện theo trạng thái, ngày nghiệp vụ và số chỗ mới được khách hàng đặt.
4. Đợt khởi hành là nguồn dữ liệu giá và chỗ trống; không sử dụng giá suy đoán từ Tour.

**Lưu ý:** tìm kiếm hiển thị tồn chỗ tại thời điểm truy vấn. Việc đặt tour thực tế mới là bước giữ chỗ có kiểm tra giao dịch.

### Bước 3 – Quản lý Booking

1. Vào **Bookings** để tìm và xem yêu cầu đặt tour.
2. Xác nhận số khách, departure, thông tin liên hệ và lịch sử trạng thái.
3. Booking `pending` giữ chỗ mặc định **30 phút**; booking chưa được xác nhận sẽ hết hạn và giải phóng chỗ theo chính sách hiện tại.
4. `confirmed` giữ chỗ; `cancelled`, `rejected`, `expired` giải phóng chỗ theo quy tắc nghiệp vụ.
5. Không xác nhận thủ công booking đã hết hạn chỉ vì đã nhận tiền; cần xử lý riêng theo chính sách tài chính.

### Bước 4 – Quản lý Thanh toán

1. Vào **Payments** (chỉ ADMIN/SUPER_ADMIN).
2. Lọc theo booking, phương thức/trạng thái giao dịch và cờ cần xử lý.
3. Ghi nhận khoản tiền nhận thực tế và kiểm tra thông tin.
4. Xác nhận payment theo quyền và quy tắc đã được phê duyệt.
5. Xem số tiền booking, đã xác nhận nhận, còn thiếu hoặc trả dư trong chi tiết Booking.

Thanh toán một phần không tự động xác nhận booking. Không tự động hoàn tiền hoặc chuyển khoản dư sang booking khác. Các khoản nhận muộn hoặc bất thường được đánh dấu để xử lý thủ công, chưa có quy trình giải quyết ngoại lệ hoàn chỉnh.

### Bước 5 – Quản lý khách hàng

1. Vào **Customers** để tạo/chỉnh sửa hồ sơ CRM.
2. Nếu muốn khách xem booking bằng tài khoản, Admin tạo CUSTOMER account và liên kết tới hồ sơ khách theo quy định.
3. Không tự liên kết booking của guest chỉ bằng email/số điện thoại.
4. Không chia sẻ thông tin đặt tour của khách cho tài khoản khác.

### Bước 6 – Lịch trình, hướng dẫn viên và vận hành

- **Itineraries:** quản lý hoạt động theo ngày/điểm dừng, thứ tự.
- **Guides:** danh sách hướng dẫn viên; phân công theo departure ở **Assignments**.
- **Suppliers:** nhà cung cấp dịch vụ.
- **Expenses:** chi phí theo chuyến/nhà cung cấp, kèm ghi chú và trạng thái.
- **Dashboard / Reports:** số liệu vận hành và tổng hợp theo quyền. Không đồng nhất giá trị booking với tiền đã thu hoặc doanh thu được công nhận.

### Bước 7 – Đăng bài Blog

1. Vào **Articles** trong Admin.
2. Tạo **Category** nếu cần.
3. Nhập Title, Slug, Body, Category, SEO Title/Description và URL ảnh nếu có.
4. Lưu `draft` để xem xét, sau đó `published` để công khai.
5. Khách xem tại `/articles` và `/articles/{slug}`.

Bài viết hiện hiển thị **plain text** có xuống dòng, chưa có bộ soạn thảo rich text. Không dán mã HTML và mong chờ nó hiển thị như giao diện HTML. URL ảnh phải là HTTP(S).

## 4. Quy trình website khách hàng

1. Mở website User và chọn **Explore tours**.
2. Dùng bộ lọc điểm đến, ngày khởi hành, số khách, thời gian, giá và tiền tệ.
3. Chỉ so sánh giá khi cùng tiền tệ; khi lọc/sắp xếp giá phải chọn tiền tệ.
4. Mở chi tiết Tour, xem lịch trình và departure có thể đặt.
5. Điền thông tin liên hệ/hành khách trong luồng **Booking**.
6. Hệ thống giữ chỗ theo chính sách pending; không coi việc gửi form là thanh toán thành công.
7. Khách có tài khoản được Admin cấp và liên kết hồ sơ có thể **Customer sign in → My bookings** để xem booking và trạng thái tiền đã ghi nhận.
8. Mở **Travel blog** để đọc các bài đã xuất bản.

**Chưa có:** khách tự đăng ký mới, quên mật khẩu hoặc thanh toán trực tuyến thật.

## 5. Hướng dẫn quản trị dữ liệu Excel/CSV

Đọc tài liệu đầy đủ tại [12_IMPORT_EXPORT_USER_GUIDE.md](./12_IMPORT_EXPORT_USER_GUIDE.md).

Nguyên tắc cốt lõi: trước khi Import phải tải mẫu → điền dữ liệu → Preview → sửa lỗi → xác nhận → kiểm tra dữ liệu Draft vừa tạo. Không có chức năng nhập làm thay đổi booking/payment.

## 6. Khởi động và dừng hệ thống local

Từ thư mục source trong Ubuntu WSL:

```bash
cp .env.example .env
# Chỉnh biến môi trường phù hợp trước khi chạy
docker compose config
docker compose up --build -d
docker compose ps
```

Dừng ứng dụng nhưng **giữ lại volume dữ liệu**:

```bash
docker compose down
```

Không dùng `docker compose down -v` nếu muốn giữ dữ liệu PostgreSQL. Chỉ chạy Alembic trên database development khi đã sao lưu và kiểm tra migration mục tiêu; tuyệt đối không dùng môi trường production cho bài test.

Các lệnh kiểm thử backend, Admin, User và PostgreSQL cách ly nằm trong `README.md` và `docs/07_WINDOWS10_WSL2_DOCKER.md`.

## 7. Các lưu ý bắt buộc

- Luôn có backup trước khi cập nhật code hoặc migration có ảnh hưởng dữ liệu.
- Không lưu API key, mật khẩu, thông tin khách hàng hay file `.env` vào GitHub public.
- Không sửa trực tiếp số ghế, trạng thái tiền hay dữ liệu booking bằng Excel.
- Không coi `npm audit fix --force` là cách sửa bảo mật an toàn.
- Mọi chức năng mới phải đi qua test/backend authorization và kiểm tra trên máy thật trước khi merge hoặc deploy.
- Khi gặp lỗi, ghi lại màn hình, thời gian, tài khoản (không kèm mật khẩu), thao tác tái hiện và HTTP status.

## 8. Liên kết tài liệu kỹ thuật

- [Kiến trúc](./02_ARCHITECTURE.md)
- [Thiết kế cơ sở dữ liệu](./03_DATABASE_DESIGN.md)
- [Backend API](./04_BACKEND_SPEC.md)
- [Admin Specification](./05_ADMIN_SPEC.md)
- [User Specification](./06_USER_SPEC.md)
- [Cài đặt Windows/WSL2/Docker](./07_WINDOWS10_WSL2_DOCKER.md)
- [Development Roadmap](./09_DEVELOPMENT_ROADMAP.md)
- [Hướng dẫn Import/Export](./12_IMPORT_EXPORT_USER_GUIDE.md)
