# TravelHub Mini Docker Controller

Dashboard HTML + Python, chỉ chạy **trên máy của bạn**. Bấm nút để build/check Local, build Public, khởi chạy hai Cloudflare Quick Tunnels có xác thực email, xem URL, backup và dừng ứng dụng.

## Chạy cực nhanh sau git pull

Từ terminal Ubuntu WSL:

```bash
cd /mnt/c/Users/Khanh/Desktop/ANY/travelhub-copilot-docs/travelhub-mini-controller
python3 server.py
```

Mở trình duyệt Windows: **http://localhost:8765**

Không cần `pip install`, không cần copy ZIP, không cần gõ các lệnh Docker dài. **Dừng panel:** Ctrl+C trong terminal đã chạy Python.

## Chuẩn bị một lần

- Có Docker daemon + Docker Compose V2; mở project trên Ubuntu WSL.
- Thư mục gốc TravelHub có `docker-compose.yml`, `docker-compose.pc-tunnel.yml`, `.env` và `.env.tunnel`.
- Nếu chưa có `.env.tunnel`, từ **root project** chạy `cp .env.tunnel.example .env.tunnel`. Quick Tunnel không cần token Named Tunnel. Không commit các file `.env*` chứa secrets.
- Đặt JWT secret production mạnh; database đã có migrations đúng, backup dữ liệu trước khi deploy.
- Dùng dữ liệu TEST. Không public khi còn thiếu giới hạn bảo mật ứng dụng.

## Nút trên giao diện

| Nút | Chức năng |
| --- | --- |
| Build & Run Local | Docker Compose dev: User :5173, Admin :5174, Backend :8000 và DB |
| Stop Local UI | Dừng Vite User/Admin, không xóa DB |
| Build & Run Public | Docker Compose overlay build Nginx User :8080 và Admin :8081 (port container nội bộ) |
| Check | Compose config, container ps, backend /health, HTML và API /api/v1/tours |
| Public User / Admin | Tạo Quick Tunnel URL ngẫu nhiên riêng, dùng `--allowed-mail` |
| Stop Tunnel / Stop Public | Dừng Tunnel và container Nginx; không xóa dữ liệu |
| Backup PostgreSQL | Sao lưu `pg_dump -Fc` vào `backups/` (được ignore bởi Git) |
| Stop All App | Dừng các container nhưng **không xóa PostgreSQL volume** |

## Bảo mật

Dashboard là công cụ đặc quyền vì có quyền gọi Docker. Chỉ lắng nghe ở `127.0.0.1:8765`, kiểm tra Host/Origin và token phiên. **Tuyệt đối không expose cổng 8765 ra LAN, Internet hoặc Cloudflare**, và không chạy controller trên VPS công khai. Không đặt Docker socket ra Internet.

Tunnel dùng email mặc định `nguyenquockhanh16032k@gmail.com`. Có thể đổi bằng biến môi trường `TRAVELHUB_ALLOWED_EMAIL` khi khởi động Python. Bạn **phải xác nhận OTP thực sự được yêu cầu**, thử email không cho phép từ thiết bị khác, sau đó đăng nhập TravelHub bằng tài khoản riêng. Email OTP không tự cấp vai trò SUPER_ADMIN.

Hai tunnel có tên Docker cố định `travelhub-quick-user` và `travelhub-quick-admin`. Nếu đóng Python bất ngờ khi tunnel còn sống, xem `docker ps -a --filter name=travelhub-quick-` rồi dừng container bằng `docker stop travelhub-quick-user travelhub-quick-admin` khi cần. Không dùng `docker compose down -v`.

Logs nội bộ nằm tại `runtime-logs/`, không đưa lên Git. Backup nằm ở `../backups/`, cần sao chép ra ổ khác và thử phục hồi định kỳ.

## Khi có lỗi

- `public-web/admin-web Restarting`: xem `docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml logs --tail=60 public-web admin-web`.
- API 500: xem `logs --tail=100 backend`, kiểm tra `alembic current` và `alembic heads`; không chạy migration khi chưa backup.
- Không thấy URL: kiểm tra log hiển thị ở dashboard, trạng thái Docker/network. Nếu CLI báo không hỗ trợ `--allowed-mail`, **không bỏ cờ và public không bảo vệ**.
- Lệnh `Build Public` có thể recreate backend, không chạy khi có người đang thực hiện booking.
- Mọi thao tác điều khiển Docker trên PC vẫn cần được kiểm thử thực tế; GitHub CI không thể xác nhận Cloudflare OTP trên máy bạn.
