# GitSeeker 部署指南（阿里云 + 现有 Nginx + 新子域名）

适用场景：服务器上已经在跑别的 gunicorn 项目 + Nginx，加一个 GitSeeker 子域名。

最终效果：浏览器访问 `http://gitseeker.yourdomain.com` 进入网站。

---

## 第 1 步：准备域名解析

去你的 DNS 控制台（阿里云 / Cloudflare / 等）加一条 A 记录：

| 主机记录 | 类型 | 值 |
|---------|-----|-----|
| `gitseeker` | A | 你的服务器公网 IP |

等 1-5 分钟生效后，`ping gitseeker.yourdomain.com` 能解析就 OK。

---

## 第 2 步：拉代码 + 装依赖

```bash
ssh root@你的服务器IP

cd /opt
git clone https://github.com/baidongli/gitseeker.git
cd gitseeker
pip3 install -r requirements.txt
```

---

## 第 3 步：配置环境变量

```bash
# 生成 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

cp .env.example .env
vi .env
```

填入：

```
SECRET_KEY=刚才生成的那串
DEBUG=False
ALLOWED_HOSTS=gitseeker.yourdomain.com
# 因为 Nginx 反代是 HTTP，这里也带 http://
CSRF_TRUSTED_ORIGINS=http://gitseeker.yourdomain.com
```

---

## 第 4 步：初始化数据库 + 静态文件

```bash
set -a; source .env; set +a
python3 manage.py migrate
python3 manage.py collectstatic --noinput
```

---

## 第 5 步：启动 Gunicorn（systemd）

```bash
# 检查 deploy/gitseeker.service 里的 User= 是否匹配你的 Nginx 用户：
# CentOS / Alibaba Linux: User=nginx
# Ubuntu / Debian:       User=www-data
# Nginx 需要能读 socket，用户必须匹配
vi deploy/gitseeker.service

cp deploy/gitseeker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now gitseeker
systemctl status gitseeker
```

确认 socket 已生成且 Nginx 用户可读：

```bash
ls -la /run/gitseeker/gunicorn.sock
# srwxrwxr-x  1 nginx nginx 0 May 21 ... /run/gitseeker/gunicorn.sock
```

---

## 第 6 步：配 Nginx 子域名

```bash
# 把示例 server 块加到你 Nginx 的 conf.d
cp deploy/nginx-gitseeker.conf /etc/nginx/conf.d/gitseeker.conf

# 改成你的实际子域名
vi /etc/nginx/conf.d/gitseeker.conf
# 把 gitseeker.example.com 改成 gitseeker.yourdomain.com

# 测试配置 + 重载
nginx -t
systemctl reload nginx
```

---

## 第 7 步：阿里云安全组（可能已开过）

如果你现有的 Nginx 已经在用 80 端口，这步直接跳过。否则：

控制台 → ECS → 安全组 → 入方向规则 → 协议 TCP / 端口 80 / 源 0.0.0.0/0

---

## 完成

浏览器访问 `http://gitseeker.yourdomain.com` —— 看到趋势页就成功了。

第一件事：去 **`/settings/`** 配 GitHub Token（限流 60/h → 5000/h）。

---

## 日常更新

```bash
cd /opt/gitseeker
git pull
pip3 install -r requirements.txt
python3 manage.py migrate
python3 manage.py collectstatic --noinput
systemctl restart gitseeker
```

可以写成 `update.sh` 一键更新：

```bash
#!/bin/bash
set -e
cd /opt/gitseeker
git pull
pip3 install -r requirements.txt --quiet
python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
systemctl restart gitseeker
echo "✓ Deployed at $(date)"
```

---

## 备份数据

数据库是单个 SQLite 文件：

```bash
cp /opt/gitseeker/db.sqlite3 ~/backups/gitseeker-$(date +%Y%m%d).sqlite3
```

定时自动备份 cron：

```cron
0 3 * * * cp /opt/gitseeker/db.sqlite3 /root/backups/gitseeker-$(date +\%Y\%m\%d).sqlite3
```

或者用 UI 的 **收藏 → 导入/导出 → 导出 JSON**。

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 502 Bad Gateway | Nginx 没权限读 socket | 把 systemd `User=` 改成 nginx 用户（nginx 或 www-data），`systemctl restart gitseeker` |
| 502 Bad Gateway | gunicorn 没起来 | `systemctl status gitseeker` + `journalctl -u gitseeker -n 50` |
| 404 (Nginx) | 域名没对上 server_name | 检查 `/etc/nginx/conf.d/gitseeker.conf` 里的 `server_name` 和你访问的域名一致 |
| `DisallowedHost` | `ALLOWED_HOSTS` 漏了 | `.env` 里加上 gitseeker.yourdomain.com，重启 |
| `CSRF verification failed` | 没加 `CSRF_TRUSTED_ORIGINS` | `.env` 里加 `CSRF_TRUSTED_ORIGINS=http://gitseeker.yourdomain.com`，重启 |
| admin 后台无样式 | 没跑 collectstatic | 第 4 步 |
| GitHub API 限流 60/h | 没配 Token | UI 设置页填 GitHub PAT |

---

## 进阶：升级 HTTPS

后续想要 HTTPS（推荐！免费而且 5 分钟）：

```bash
# 装 certbot
yum install -y certbot python3-certbot-nginx
# 或: apt install -y certbot python3-certbot-nginx

# certbot 自动改 Nginx 配置 + 申请 Let's Encrypt 证书
certbot --nginx -d gitseeker.yourdomain.com

# 自动续期已经配好了，不用管
```

certbot 跑完后，浏览器访问 `https://gitseeker.yourdomain.com` 即可。

记得回 `.env` 把 `CSRF_TRUSTED_ORIGINS` 改成 `https://...`，重启 gitseeker。

---

## 看日志

```bash
# Gunicorn 进程日志
journalctl -u gitseeker -f

# Nginx 访问/错误日志
tail -f /var/log/nginx/gitseeker-access.log
tail -f /var/log/nginx/gitseeker-error.log
```
