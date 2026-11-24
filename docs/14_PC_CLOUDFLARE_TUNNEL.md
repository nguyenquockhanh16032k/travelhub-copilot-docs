# TravelHub trên PC với Cloudflare Tunnel (HTTPS, không mở cổng)

Tài liệu này dành cho môi trường PC cá nhân chạy Windows + Ubuntu WSL2 + Docker Compose. **Đây là phương án public thử nghiệm có kiểm soát**, không phải triển khai VPS/production được chứng nhận. Bản cấu hình chỉ công khai **website khách hàng**, không đưa Admin, PostgreSQL hay API docs lên Internet.

## 1. Kiến trúc

```text
Internet (HTTPS)
       |
 Cloudflare Access (bắt buộc ở giai đoạn thử nghiệm)
       |
 Cloudflare Tunnel (outbound only)
       |
 cloudflared (tunnel_edge network)
       |
 public-web Nginx (:8080, Docker internal, NO host port)
       |-- /            → Vue User static build
       └-- /api/v1/     → FastAPI backend:8000 (Docker network)
                               |
                              db:5432 (Docker private)
```

Không công khai Vite 5173/5174, FastAPI 8000, database 5432 ra Internet. Admin vẫn dùng `http://localhost:5174` tại PC. Nhờ API same-origin `/api/v1`, frontend không cần biết địa chỉ `localhost:8000` từ browser khách.

## 2. Điều kiện bắt buộc

- Docker và Docker Compose phải hoạt động trong WSL2.
- Backup PostgreSQL trước khi thay đổi cấu hình runtime.
- `.env` phải có `JWT_SECRET_KEY` là chuỗi ngẫu nhiên **từ 32 ký tự trở lên**, không phải placeholder.
- Hiểu rằng overlay PC thay đổi lệnh backend từ `uvicorn --reload` sang `uvicorn --workers 1`, đặt `ENVIRONMENT=production` để bật kiểm tra JWT secret. Overlay dùng **lại PostgreSQL volume development hiện tại**, không tự tạo database khác.
- Cloudflare account và **domain DNS quản lý bởi Cloudflare** để dùng hostname ổn định. Domain mua có thể phát sinh phí; Tunnel/Access có gói miễn phí trong giới hạn.
- Chưa bật chế độ public ai cũng vào khi còn các cảnh báo bảo mật npm/pip và chưa có rate limiting cho login/booking.
- PC phải bật, Docker và Internet hoạt động liên tục.

## 3. Tạo Tunnel trên Cloudflare

1. Mở [Cloudflare Zero Trust](https://one.dash.cloudflare.com/).
2. Trong Networks / Connectors → Tunnels, chọn **Create tunnel** (tên có thể thay đổi theo giao diện Cloudflare).
3. Đặt tên ví dụ `travelhub-pc`, chọn Docker connector.
4. Sao chép **chỉ token** từ lệnh Docker mà Cloudflare hiển thị.
5. Tạo hostname công khai như `travel.example.com`, trỏ service tới **`http://public-web:8080`**.
6. Không cấu hình các hostname khác, đặc biệt không trỏ tới `backend:8000`, `db:5432`, `admin:5174` hay Docker host.

Đừng gửi token lên chat, đừng commit token vào GitHub.

### Cloudflare Access – giới hạn người được dùng khi thử nghiệm

Trước khi chạy tunnel với hostname public, tạo **Access application (Self-hosted)** cho hostname `travel.example.com`, quy tắc **Allow only** địa chỉ email bạn và người thử nghiệm được chọn. Kiểm tra từ một thiết bị không đăng nhập để xác nhận trang yêu cầu xác thực Cloudflare Access.

Khi nào khắc phục xong security advisories và login/booking rate limiting, mới cân nhắc gỡ Access cho website khách. **Không gỡ Access cho Admin** khi có hostname riêng trong tương lai.

Tham khảo: [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/get-started/) và [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/applications/).

## 4. Bật trên PC

Trong thư mục project, từ Ubuntu WSL:

```bash
cp .env.tunnel.example .env.tunnel
chmod 600 .env.tunnel
```

Mở file `.env.tunnel` bằng editor, thay `TUNNEL_TOKEN` bằng token thật từ dashboard (không thêm vào `.env.example` hoặc Git).

Đảm bảo `.gitignore` bỏ qua `.env.tunnel`, và `.env` có JWT secret đủ mạnh; không đổi password DB/URL đang chạy một cách tùy tiện.

Kiểm tra cấu hình Docker:

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml config --quiet
```

**Cẩn thận:** `docker compose config` không có `--quiet` có thể in tunnel token vào terminal/log.

Chạy công khai (vẫn có Cloudflare Access bảo vệ):

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml up -d --build public-web cloudflared
```

Kiểm tra trạng thái mà không in secret:

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml ps
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml logs --tail=50 cloudflared
```

Trên điện thoại bằng 4G/5G, truy cập HTTPS hostname, xác nhận Cloudflare Access yêu cầu xác thực trước khi vào trang, sau đó kiểm tra Tour, Blog, và API qua frontend. **Không tạo booking thật trong lúc thử nghiệm nếu chính sách bảo mật chưa được triển khai.**

### Tắt tunnel

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml stop cloudflared public-web
```

Lệnh này chỉ dừng hai service tunnel/web, không xóa database.

## 5. An toàn và giới hạn

- Cloudflare Tunnel tạo kết nối outbound, giảm rủi ro mở cổng router, **không tự sửa lỗi ứng dụng**. Auth, RBAC, CSRF/XSS, brute-force, lộ dữ liệu, dependency vulnerabilities vẫn phải được xử lý.
- API dùng same-origin và đi qua Nginx, nhưng endpoint có route `/api/v1/` vẫn có thể truy cập bởi người đã qua Access. Không xem Tunnel như cơ chế xác thực API.
- Không mở Admin public trên cấu hình này; Admin chỉ dùng localhost/VPN riêng cho đến khi Cloudflare Access cho Admin được triển khai và test.
- Nginx phục vụ Vue build tĩnh; Vite dev server không mở public.
- Do vẫn dùng Compose development, backend đang bind mount source; không sửa code nóng khi người khác đang dùng.
- Cloudflare token bị lộ: rotate hoặc revoke ngay ở dashboard.
- Backup PostgreSQL ra ổ đĩa khác và kiểm thử restore thường xuyên.
- Domain có thể mất phí dù Tunnel và Access có gói miễn phí.
- Không dùng `docker compose down -v` trên môi trường dữ liệu thật.

## 6. Khi có lỗi

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Cloudflare 1033 / hostname không truy cập được | Kiểm tra tunnel `Healthy` và DNS route trong Cloudflare |
| 502 | Kiểm tra `public-web`, backend health, tên origin `http://public-web:8080` |
| 403 ngay từ Cloudflare Access | Kiểm tra Allow policy và email thử nghiệm |
| Lỗi API trên trình duyệt | Kiểm tra Network: request phải là `https://<hostname>/api/v1/...` |
| Container backend từ chối khởi động | Kiểm tra `JWT_SECRET_KEY` đủ mạnh và `DATABASE_URL` đúng |
| Mất truy cập khi tắt PC | Đây là hành vi bình thường, PC chính là host |
| Backend localhost đang chạy trước đó bị restart | Overlay thay đổi backend configuration; nếu cần dev --reload, dừng tunnel và chạy lại Compose mặc định |

## 7. Đang chờ trước khi mở public rộng

- Chạy CI đầy đủ trên nhánh.
- Xử lý security advisories nghiêm trọng liên quan đến auth/web framework.
- Thêm rate limiting cho login và booking.
- Kiểm thử backup/restore; không chỉ backup mà phải xác nhận restore được.
- Kiểm thử access policy từ một thiết bị bên ngoài.
- Xác nhận miền/hostname thực tế.

Cấu hình này không tự tạo Tunnel hay URL nếu chưa có token, domain và cấu hình Dashboard Cloudflare do chủ tài khoản thực hiện.
