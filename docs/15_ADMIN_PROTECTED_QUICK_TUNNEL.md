# TravelHub Admin qua Quick Tunnel có xác minh email (không cần domain)

Chỉ dùng thử nghiệm trên PC Windows + WSL2 + Docker. **Không có URL cố định.** Phải bật bảo vệ email `--allowed-mail` và **vẫn đăng nhập vào TravelHub**. Không công khai cổng 5174 của Vite dev server hoặc backend/database.

## Cấu hình

- Website khách: `public-web:8080`, tunnel riêng nếu cần.
- Admin: `admin-web:8081`, Nginx static build + reverse-proxy `/api/v1/` đến FastAPI.
- Cloudflare Quick Tunnel cấp URL ngẫu nhiên `https://….trycloudflare.com`, chỉ cho email được cấu hình xác minh bằng OTP.
- Admin vẫn cần tài khoản TravelHub có role `SUPER_ADMIN` (khác với `ADMIN`). OTP Cloudflare **không** cấp quyền trong database.
- Mọi URL `/api/v1/` qua hostname Admin đều được che bởi cùng lớp OTP, nhưng Backend vẫn phải kiểm tra RBAC trên từng API.

## Trước khi chạy

1. Sao lưu PostgreSQL, chỉ dùng dữ liệu thử nghiệm, JWT secret đủ mạnh.
2. Chạy Docker và kiểm tra backend `healthy`, migration `alembic current` phù hợp với `alembic heads`.
3. Nếu đang chạy Quick Tunnel khách hàng ở một terminal khác, giữ nguyên; Admin dùng terminal riêng.
4. Cập nhật code local: `git pull origin main` **sau khi PR này được merge**. Thay đổi YAML local trước đó có thể cần `git stash` hoặc xử lý xung đột; đừng ghi đè thay đổi chưa lưu.

## Chạy Admin Nginx

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml up -d --build admin-web
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml ps admin-web
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml exec admin-web wget -qO- http://127.0.0.1:8081/ | head -c 200
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml exec admin-web wget -qO- http://127.0.0.1:8081/api/v1/tours | head -c 200
```

## Mở Quick Tunnel Admin (tại terminal khác)

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml run --rm --no-deps -e TUNNEL_TOKEN= cloudflared tunnel --url http://admin-web:8081 --allowed-mail nguyenquockhanh16032k@gmail.com
```

- Đảm bảo log xác nhận **email authentication enabled** rồi mới dùng URL. Nếu lệnh không hỗ trợ cờ `--allowed-mail`, **không** bỏ cờ để mở công khai; cập nhật image cloudflared mới.
- Mở URL qua điện thoại 4G, xác minh OTP email, sau đó đăng nhập bằng **mật khẩu TravelHub**. Dùng trình duyệt khác/email khác để xác nhận truy cập bị chặn.
- Đóng terminal hoặc nhấn `Ctrl+C` để dừng tunnel. Tắt toàn bộ app trên PC cũng làm URL không truy cập được.
- Không gửi OTP, token, mật khẩu hoặc file `.env` lên GitHub/chat.

## Cấp vai trò SUPER_ADMIN — thực hiện riêng, không tự động

Kiểm tra quyền hiện có sau đăng nhập:
`GET /api/v1/auth/me` (trong trình duyệt Admin sau khi có phiên hợp lệ).
Role `SUPER_ADMIN` có toàn bộ quyền hiện được hệ thống định nghĩa; `ADMIN` không có `users:manage_admin` hay `system:settings`.

Không cấp `SUPER_ADMIN` chỉ dựa vào quyền sở hữu địa chỉ email Cloudflare. Quản trị viên cần **xác thực danh tính và tài khoản TravelHub**, kiểm tra trạng thái hiện hữu, sao lưu DB rồi mới chạy quy trình bootstrap/quản trị role có kiểm toán. PR này không cập nhật DB hoặc tạo mật khẩu mới.

## Giới hạn bảo mật

Cấu hình này phục vụ demo/thử nghiệm, không phải production: login/booking rate limiting và dependency advisories còn phải xử lý; cần xác minh lại chức năng OTP. Dù Admin qua Tunnel được xác thực, API/backend localhost và website khách chạy riêng trên PC vẫn là các lối truy cập khác. Không dùng dữ liệu thật trước khi đánh giá bảo mật đầy đủ.
