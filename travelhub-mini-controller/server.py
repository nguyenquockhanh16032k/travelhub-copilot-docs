#!/usr/bin/env python3
"""TravelHub Docker controller: local-only, Python standard library."""
from __future__ import annotations

import json
import os
import re
import secrets
import signal
import subprocess
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
HOST = "127.0.0.1"
PORT = int(os.getenv("TRAVELHUB_PANEL_PORT", "8765"))
EMAIL = os.getenv("TRAVELHUB_ALLOWED_EMAIL", "nguyenquockhanh16032k@gmail.com")
TOKEN = secrets.token_urlsafe(32)
BASE = ["docker", "compose", "-f", "docker-compose.yml"]
PUBLIC = BASE + ["-f", "docker-compose.pc-tunnel.yml"]
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)
EDGE = {"user": ("public-web", "8080"), "admin": ("admin-web", "8081")}
LOGS = HERE / "runtime-logs"
LOGS.mkdir(exist_ok=True)
STATE_LOCK = threading.RLock()
STATE = {"job": None, "tunnels": {}}


def run(args, timeout=900):
    p = subprocess.run(args, cwd=PROJECT, text=True, capture_output=True,
                       errors="replace", timeout=timeout)
    output = (p.stdout + "\n" + p.stderr).strip()
    if p.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{output[-6000:]}")
    return output[-8000:]


def prereqs(public=False):
    names = ["docker-compose.yml", ".env"]
    if public:
        names += ["docker-compose.pc-tunnel.yml", ".env.tunnel"]
    missing = [n for n in names if not (PROJECT / n).is_file()]
    if missing:
        raise RuntimeError("Thiếu: " + ", ".join(missing))
    if not public:
        return
    # The overlay contains an optional named-tunnel service; Quick Tunnel does not use its token.


def stop_tunnel(which):
    if which not in EDGE:
        raise RuntimeError("Unknown tunnel")
    name = "travelhub-quick-" + which
    proc = None
    with STATE_LOCK:
        proc = STATE["tunnels"].pop(which, None)
    # docker stop ONLY our exact named quick-tunnel container
    check = subprocess.run(["docker", "container", "inspect", name], cwd=PROJECT,
                           capture_output=True, timeout=10)
    if check.returncode == 0:
        run(["docker", "stop", "--time", "3", name], timeout=25)
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    return "Đã dừng Quick Tunnel " + which


def start_tunnel(which):
    if which not in EDGE:
        raise RuntimeError("Unknown tunnel")
    prereqs(True)
    service, port = EDGE[which]
    status = run(PUBLIC + ["ps", "--status", "running", "--services"], 20)
    if service not in status.splitlines():
        raise RuntimeError("Chưa có " + service + " đang chạy. Build Public trước.")
    name = "travelhub-quick-" + which
    if subprocess.run(["docker", "container", "inspect", name], cwd=PROJECT,
                      capture_output=True, timeout=10).returncode == 0:
        raise RuntimeError("Container " + name + " đã tồn tại; dừng tunnel cũ trước.")
    args = PUBLIC + ["run", "--rm", "--no-deps", "--name", name, "-e", "TUNNEL_TOKEN=",
                     "cloudflared", "tunnel", "--url", f"http://{service}:{port}",
                     "--allowed-mail", EMAIL]
    with (LOGS / ("tunnel-" + which + ".log")).open("w", encoding="utf-8") as out:
        proc = subprocess.Popen(args, cwd=PROJECT, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
    with STATE_LOCK:
        STATE["tunnels"][which] = proc
    return "Đã chạy Tunnel " + which + "; đợi URL và kiểm tra OTP trước khi chia sẻ."


def do_action(action):
    if action == "local-start":
        prereqs()
        steps = [BASE + ["config", "--quiet"], BASE + ["up", "-d", "--build",
                 "db", "backend", "user", "admin"], BASE + ["ps"]]
    elif action == "public-start":
        prereqs(True)
        steps = [PUBLIC + ["config", "--quiet"], PUBLIC + ["up", "-d", "--build",
                 "db", "backend", "public-web", "admin-web"], PUBLIC + ["ps"]]
    elif action == "local-stop":
        steps = [BASE + ["stop", "user", "admin"]]
    elif action == "public-stop":
        stop_tunnel("user")
        stop_tunnel("admin")
        steps = [PUBLIC + ["stop", "public-web", "admin-web"]]
    elif action == "stop-all":
        stop_tunnel("user")
        stop_tunnel("admin")
        steps = [PUBLIC + ["stop", "public-web", "admin-web",
                          "user", "admin", "backend", "db"]]
    elif action == "check":
        prereqs(True)
        steps = [PUBLIC + ["config", "--quiet"], PUBLIC + ["ps"],
                 ["curl", "-fsS", "http://127.0.0.1:8000/health"]]
        for service, port in EDGE.values():
            steps += [PUBLIC + ["exec", "-T", service, "wget", "-qO-",
                       f"http://127.0.0.1:{port}/"],
                      PUBLIC + ["exec", "-T", service, "wget", "-qO-",
                       f"http://127.0.0.1:{port}/api/v1/tours"]]
    elif action == "backup":
        prereqs()
        dest = PROJECT / "backups"
        dest.mkdir(exist_ok=True)
        target = dest / ("travelhub-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".dump")
        try:
            with target.open("wb") as f:
                p = subprocess.run(BASE + ["exec", "-T", "db", "sh", "-c",
                    'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'],
                    cwd=PROJECT, stdout=f, stderr=subprocess.PIPE, timeout=120)
            if p.returncode or target.stat().st_size < 20:
                raise RuntimeError(p.stderr.decode(errors="replace")[-1000:])
            return f"Backup: {target} ({target.stat().st_size} bytes). Hãy sao lưu thêm ra ổ khác."
        except Exception:
            target.unlink(missing_ok=True)
            raise
    else:
        raise RuntimeError("Unsupported action")
    result = []
    for command in steps:
        result.append("$ " + " ".join(command) + "\n" + run(command))
    return "\n\n".join(result)[-12000:]


def run_job(action):
    with STATE_LOCK:
        if STATE["job"] and STATE["job"]["state"] == "running":
            raise RuntimeError("Đang có tác vụ chạy. Chờ tác vụ đó hoàn thành.")
        STATE["job"] = {"name": action, "state": "running", "message": "Đang thực hiện..."}

    def worker():
        try:
            output = do_action(action)
            status = "success"
        except Exception as e:
            output = str(e)
            status = "error"
        with STATE_LOCK:
            STATE["job"] = {"name": action, "state": status, "message": output}
        with (LOGS / "actions.log").open("a", encoding="utf-8") as f:
            f.write(f"\n{datetime.now().isoformat()} {action}: {status}\n{output}\n")
    threading.Thread(target=worker, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def response(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def guard(self, write=False):
        host = self.headers.get("Host", "").split(":")[0]
        origin = self.headers.get("Origin", "")
        if host not in ("localhost", "127.0.0.1"):
            self.response({"error": "Invalid Host"}, 403)
            return False
        if write and (origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}") or
                      self.headers.get("X-TravelHub-Token") != TOKEN):
            self.response({"error": "Invalid Origin or Token"}, 403)
            return False
        return True

    def do_GET(self):
        if not self.guard():
            return
        if self.path == "/":
            html = (HERE / "index.html").read_text(encoding="utf-8")
            html = html.replace("__TOKEN__", TOKEN).replace("__EMAIL__", EMAIL)
            data = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/api/status":
            with STATE_LOCK:
                job = STATE["job"]
                procs = dict(STATE["tunnels"])
            tunnels = {}
            for name in EDGE:
                p = procs.get(name)
                log = LOGS / f"tunnel-{name}.log"
                info = log.read_text(encoding="utf-8", errors="replace")[-6000:] if log.exists() else ""
                urls = URL_PATTERN.findall(info)
                tunnels[name] = {"running": p is not None and p.poll() is None,
                                 "url": urls[-1] if urls and p is not None and p.poll() is None else "",
                                 "log": info[-800:]}
            self.response({"job": job, "tunnels": tunnels})
            return
        self.response({"error": "Not found"}, 404)

    def do_POST(self):
        if not self.guard(write=True):
            return
        if self.headers.get("Content-Length", "0") not in ("0", "2"):
            self.response({"error": "Unexpected body"}, 400)
            return
        try:
            if self.path.startswith("/api/action/"):
                action = self.path.removeprefix("/api/action/")
                if action not in {"local-start", "public-start", "local-stop", "public-stop", "stop-all", "check", "backup"}:
                    raise RuntimeError("Unknown action")
                run_job(action)
                message = "Đã nhận lệnh."
            else:
                m = re.fullmatch(r"/api/tunnel/(user|admin)/(start|stop)", self.path)
                if not m:
                    self.response({"error": "Not found"}, 404)
                    return
                message = start_tunnel(m[1]) if m[2] == "start" else stop_tunnel(m[1])
            self.response({"ok": True, "message": message})
        except Exception as e:
            self.response({"error": str(e)}, 409)


if __name__ == "__main__":
    if not (PROJECT / "docker-compose.yml").exists():
        raise SystemExit("Đặt travelhub-mini-controller trong root TravelHub (cạnh docker-compose.yml).")
    print(f"TravelHub Mini Controller: http://localhost:{PORT}", flush=True)
    print("Chỉ truy cập trên PC; tuyệt đối không đưa cổng 8765 lên Internet.", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
