# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Deploy Targets

### Dev (this WSL2 machine)
- FastAPI port 8000 serves `/static/` from `frontend/`
- Nginx port 5080 (catch-all `server_name _;`) proxies `/static/` → port 8000
- File sync: `frontend/` ⇄ `static/` (both must match)
- URL: `http://localhost:8000/editor.html`

### Prod (10.0.0.58 nginx 1.31.2)
- **Nginx directly serves `/static/*` from `/opt/webfilebot/webbot/frontend/`**
  NOT from `static/` directory — the FastAPI `static/` mount is NOT routed on prod
- Other paths proxy to port 8000 on this WSL2 machine
- URL: `https://prod.webfilebot.com/static/editor.html`
- **Deploy target for static files:** `/opt/webfilebot/webbot/frontend/`

### Cloudflare Tunnel
- Runs on this WSL2 machine (`root`), routes to port 5080 (nginx)
- `prod.webfilebot.com` → Cloudflare → nginx 5080 → decides based on path:
  - `/static/*` → FastAPI 8000 (locally) OR served directly by prod nginx
  - Other → FastAPI 8000

### Also: nginx catch-all static dir
- `/var/www/filebot-frontend/` — for other domains matching `server_name _;`

### 生产 webbot (10.0.0.58:8000)
- 代码: `/opt/webfilebot/webbot/app/`（与 dev 同步，md5 一致）
- **真实 DB: `/opt/webfilebot/webbot/data/webbot.db`** (1.4GB, 24K+ 页)。⚠️ `app/webbot.db` 只是 98KB 空壳！
- **重启：`sudo systemctl restart webbot`**（systemd 服务 `/etc/systemd/system/webbot.service`，已配 WEBBOT_DB_PATH=/opt/webfilebot/webbot/data/webbot.db，Restart=always 自动拉起）⚠️ 不要手动 nohup 启动（会与 systemd 进程抢 8000 端口，且 systemd 会自动拉起导致多进程混乱）；pkill -f 'uvicorn app.main' 会误杀自己的 ssh 会话（命令行含同字符串），慎用
- 日志：`journalctl -u webbot --no-pager -n 50`（旧日志文件 webbot_run.log 仅手动启动时才有）
- 日志: `/opt/webfilebot/webbot/webbot_run.log`
- 生产 nginx 挂载源: `/opt/webfilebot/nginx/conf.d/`（改后 `docker exec wb-nginx nginx -t && nginx -s reload`）
  - `filebot-app.conf` = prod.webfilebot.com（SPA fallback + `~ ^/(en|fr)(/|$)` → 172.18.0.1:8000 动态渲染）
  - `ca-site.conf` = canadasite.webfilebot.com（静态 publish 8003 + auth_request，未登录 302 → prod login）
  - `default.conf` = catch-all（en/fr 静态 publish 文件 + API + publish-batch）
- 动态页面路由: `/en` `/fr` `/en/{path:path}` `/fr/{path:path}`（main.py，DB 实时渲染，复用 `_render_preview`，支持 `.html` 后缀）
- 公网链路: CF → 生产机 cloudflared tunnel → 生产 nginx（本机 5080 不是 prod 域名 origin！）

---

Add whatever helps you do your job. This is your cheat sheet.
