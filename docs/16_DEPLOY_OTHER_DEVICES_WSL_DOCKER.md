# Deploy TravelHub từ Windows/WSL2 để truy cập bằng thiết bị khác (không cần domain)

Hướng dẫn này áp dụng cho repo TravelHub hiện tại: Docker Compose, FastAPI, PostgreSQL, Vue User/Admin build tĩnh qua Nginx, Cloudflare Quick Tunnel. Chạy từ **Ubuntu WSL** tại thư mục gốc repo, ví dụ:

```bash
cd /mnt/c/Users/Khanh/Desktop/ANY/travelhub-copilot-docs
```

> **Mục đích: demo/test có kiểm soát**, không phải production. Máy PC phải bật, WSL/Docker và mạng hoạt động. URL Quick Tunnel thay đổi khi tạo lại. Không mở router, không public Vite dev server, cổng backend hay DB. Chỉ sử dụng dữ liệu thử nghiệm. Cloudflare OTP và quyền SUPER_ADMIN trong TravelHub là **hai lớp xác thực độc lập**.

## A. Trước khi cập nhật source: giữ thay đổi local

```bash
git status --short
git branch --show-current
```

Nếu đã tự sửa `docker-compose.pc-tunnel.yml`, giữ lại trước khi pull:

```bash
cp docker-compose.pc-tunnel.yml docker-compose.pc-tunnel.yml.backup
git stash push -m "local tunnel YAML backup" -- docker-compose.pc-tunnel.yml
git checkout main
git pull --ff-only origin main
```

Không chạy `git reset --hard` hay `git clean -fd` để 'sửa nhanh'. Nếu `git checkout` hoặc `git pull` báo các thay đổi ở file **khác**, dừng lại, xem `git status` và xử lý riêng; tránh mất công việc. Sau khi pull, kiểm tra dịch vụ `admin-web` và quyền Nginx đã có trong YAML mới, **không áp dụng lại stash mù quáng**.

## B. Kiểm tra prerequisites và bí mật

```bash
docker version
docker compose version
docker info >/dev/null && echo "Docker daemon OK"
test -f .env && echo ".env exists"
test -f .env.tunnel && echo ".env.tunnel exists"
git check-ignore .env .env.tunnel
```

- `.env` phải có `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET_KEY` ngẫu nhiên dài ít nhất 32 ký tự, không phải placeholder; không in secret ra terminal/chat.
- `.env.tunnel` được overlay dùng cho service named-tunnel (dù chạy Quick Tunnel). Nếu **chưa có** file: `cp .env.tunnel.example .env.tunnel`; Quick Tunnel không cần token thật. **Không** commit file chứa token.
- `git check-ignore` phải hiển thị cả hai file; nếu không, kiểm tra `.gitignore` trước khi tiếp tục.
- Quick Tunnel sử dụng **một container cloudflared chạy tạm bằng `docker compose run`**, KHÔNG dùng `docker compose up cloudflared` (lệnh sau dành cho named tunnel, cần token/domain).
- Đã sao lưu PostgreSQL ở bước C và khôi phục thử định kỳ; chưa dùng dữ liệu cá nhân thật. Kiểm tra trạng thái cảnh báo bảo mật và rate limiting trước khi định hướng sản xuất.

## C. Sao lưu PostgreSQL trước khi deploy

Nếu DB đã chạy, sao lưu trực tiếp từ service `db` trong thư mục gốc dự án:

```bash
mkdir -p backups
docker compose exec -T db sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/travelhub-before-deploy.dump
test -s backups/travelhub-before-deploy.dump && echo "Backup file not empty"
```

Giữ file backup **ngoài Git**, tốt nhất sao chép sang ổ an toàn khác; xác minh quy trình restore theo `docs/07_WINDOWS10_WSL2_DOCKER.md`. Nếu backup lỗi hoặc rỗng, **không nâng cấp schema**. Không dùng `docker compose down -v`.

## D. Validate / build / start (User + Admin)

Lệnh dài được viết bằng biến shell, giảm nhầm file Compose. Chạy trong **cùng terminal**:

```bash
dc() { docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml "$@"; }
dc config --quiet
dc build backend public-web admin-web
dc up -d --no-build db backend public-web admin-web
dc ps
```

Lần đầu build có thể kéo Node/Nginx/Python images. Không cần chạy `user` / `admin` Vite dev để public. Trong overlay, backend được đặt ở `ENVIRONMENT=production`, nên JWT secret phải đủ mạnh. `db` và `backend` cần `healthy`; `public-web` và `admin-web` cần `Up` (không `Restarting`).

Nếu vừa thay đổi mã nguồn, build lại:

```bash
dc up -d --build backend public-web admin-web
```

Điều này có thể recreate backend, ảnh hưởng phiên test đang chạy, nhưng **không xóa PostgreSQL volume**.

## E. Smoke checks bắt buộc, trước khi bật Tunnel

```bash
# API trực tiếp trên PC (health endpoint ở /health, KHÔNG phải /api/v1/health)
curl -fsS http://127.0.0.1:8000/health && echo

# User SPA qua Nginx nội bộ (phải có <!doctype html>)
dc exec -T public-web wget -qO- http://127.0.0.1:8080/ | head -c 200; echo

# Admin SPA qua Nginx nội bộ
dc exec -T admin-web wget -qO- http://127.0.0.1:8081/ | head -c 200; echo

# Backend API qua Nginx, phải có JSON "items"
dc exec -T public-web wget -qO- http://127.0.0.1:8080/api/v1/tours | head -c 300; echo
dc exec -T admin-web wget -qO- http://127.0.0.1:8081/api/v1/tours | head -c 300; echo
```

Không đánh giá `/api/v1/health` để test kết nối: backend chỉ khai báo `/health` ở root và Nginx chủ ý chặn `/health` công khai. Nếu API Tour trả `500`, **dừng tại đây**, xem `dc logs --tail=100 backend`. Lỗi từng gặp là PostgreSQL thiếu cột `bookings.expires_at` do migration chưa đồng bộ. Kiểm tra:

```bash
dc exec backend alembic current
dc exec backend alembic heads
```

Chỉ chạy `dc exec backend alembic upgrade head` **sau backup, xác minh migration và hiểu ảnh hưởng của thay đổi schema**; không chạy `alembic stamp head` để che lỗi, không tự chỉnh SQL.

Khi Nginx liên tục `Restarting`:

```bash
dc logs --tail=80 public-web
dc logs --tail=80 admin-web
```

Cấu hình `cap_drop: ALL` cùng `cap_add: [CHOWN, SETUID, SETGID]` phải thuộc **service** `public-web` / `admin-web`, không nằm dưới `networks.tunnel_edge`. `dc config --quiet` bắt lỗi thụt dòng. Không cần `cap_add: ALL`.

## F. Public HTTPS qua Cloudflare Quick Tunnel — hai cửa sổ terminal

**Bắt buộc bật giới hạn email.** Các lệnh dưới đây dựa trên cờ `--allowed-mail` của `cloudflared` Quick Tunnel; nếu CLI từ chối hoặc không hiển thị xác thực OTP khi test, **dừng Tunnel bằng Ctrl+C, không bỏ cờ để mở công khai**. Không khẳng định có bảo vệ nếu chưa thử bằng trình duyệt ẩn danh và email không được phép.

Terminal **A** dành cho User:

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml run --rm --no-deps \
  -e TUNNEL_TOKEN= cloudflared \
  tunnel --url http://public-web:8080 \
  --allowed-mail nguyenquockhanh16032k@gmail.com
```

Terminal **B** dành cho Admin (không đóng Terminal A):

```bash
docker compose -f docker-compose.yml -f docker-compose.pc-tunnel.yml run --rm --no-deps \
  -e TUNNEL_TOKEN= cloudflared \
  tunnel --url http://admin-web:8081 \
  --allowed-mail nguyenquockhanh16032k@gmail.com
```

Mỗi terminal phải in một URL khác nhau `https://<random>.trycloudflare.com`. Không dùng `localhost:5173` / `localhost:5174` trong URL Tunnel. Tunnel và Nginx cùng Docker network `tunnel_edge`; Nginx proxy đến backend trên default network.

Nếu CLI không hỗ trợ `--allowed-mail`: kiểm tra `docker compose ... run --rm --no-deps -e TUNNEL_TOKEN= cloudflared tunnel --help` (không đưa token vào log), sau đó chọn giải pháp bảo vệ khác; **không public Admin trần**.

### Kiểm tra thực tế trên thiết bị khác

1. Trên điện thoại **tắt Wi-Fi, bật 4G/5G**; mở URL **User**. Trình duyệt phải yêu cầu xác minh email. Thử email ngoài danh sách: phải bị từ chối.
2. Mở URL **Admin** ở trình duyệt riêng. Phải có bước OTP email `nguyenquockhanh16032k@gmail.com` trước trang đăng nhập.
3. Đăng nhập TravelHub Admin bằng tài khoản ứng dụng riêng, kiểm tra Dashboard/Tour. **OTP Cloudflare không tự cấp role SUPER_ADMIN**; kiểm tra `GET /api/v1/auth/me` sau khi đăng nhập (cần access token). Nếu không có role, sử dụng quy trình bootstrap/quản trị tài khoản hợp lệ, không chỉnh thẳng role theo email mà chưa xác minh.
4. Kiểm tra tab Network trong browser: mọi request phải đi đến chính hostname HTTPS đó, với đường dẫn `/api/v1/` (không phải `localhost:8000`).
5. Thử reload trực tiếp URL sâu của SPA (ví dụ trang Dashboard) để xác nhận Nginx fallback `index.html`.
6. Nếu trang mở ngay không cần OTP hoặc có lỗi đăng nhập/403/5xx, **dừng và sửa** trước khi chia sẻ URL cho tester.

**Dừng:** `Ctrl+C` ở mỗi terminal đang chạy Quick Tunnel. Dừng Nginx nhưng giữ DB:

```bash
dc stop public-web admin-web
```

Khi tắt PC/WSL/Docker, URL cũng ngừng hoạt động.

## G. Debug nhanh

| Lỗi | Kiểm tra |
| --- | --- |
| `config --quiet` lỗi YAML | Sai indent dưới `services:`; các capabilities không được nằm trong `networks:` |
| Backend `unhealthy` | `dc logs --tail=80 backend`; production cần JWT secret mạnh |
| `public-web` / `admin-web` Restarting | `dc logs --tail=80 <service>`; quyền Nginx, read-only cache, syntax |
| HTML OK, API Tour 500 | `dc logs --tail=120 backend`; migration Postgres, kiểm tra Alembic |
| Quick Tunnel không có URL | Kiểm tra `cloudflared` log/DNS/UDP, giữ terminal mở; service đã `Up` |
| Quick Tunnel `--allowed-mail` không hợp lệ | Dừng; kiểm tra phiên bản/CLI hoặc chọn biện pháp bảo vệ khác |
| Truy cập bằng điện thoại không được | Dùng URL `trycloudflare.com` chứ không dùng `localhost`; PC phải bật |
| Trang hiện nhưng API lỗi CORS/localhost | Build phải dùng `VITE_API_BASE_URL=/api/v1` trong Dockerfile static |
| Email OTP qua được nhưng Admin 403 | Kiểm tra role TravelHub `SUPER_ADMIN` và quyền backend |
| Không muốn public nữa | `Ctrl+C` ở cả hai cửa sổ Quick Tunnel, kiểm tra container tạm đã dừng |

> Không gửi token, mật khẩu, mã OTP, `.env`, `.env.tunnel` hay bản dump PostgreSQL lên chat/issue/GitHub. Các lệnh Docker được thiết kế để kiểm tra trên PC; **không có xác nhận deploy thành công từ CI** nếu chưa chạy smoke tests và thử nghiệm trên thiết bị thật.
