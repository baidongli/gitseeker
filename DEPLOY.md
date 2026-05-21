# GitSeeker 阿里云部署指南（IP + HTTP + SQLite）

适用：阿里云 ECS / 轻量服务器，10 分钟搞定，无需域名和 HTTPS。

---

## 第 1 步：服务器准备

SSH 登录服务器：

```bash
ssh root@你的服务器IP
```

确认 Python 3.9+ 已装：

```bash
python3 --version
# 没装的话：
# CentOS/Alibaba Linux:  yum install -y python3 python3-pip git
# Ubuntu/Debian:         apt update && apt install -y python3 python3-pip git
```

---

## 第 2 步：拉代码 + 装依赖

```bash
cd /opt
git clone https://github.com/baidongli/gitseeker.git
cd gitseeker
pip3 install -r requirements.txt
```

---

## 第 3 步：配置环境变量

```bash
# 生成一个 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# 复制示例文件
cp .env.example .env
vi .env
```

填入（举例）：

```
SECRET_KEY=刚才生成的那串
DEBUG=False
ALLOWED_HOSTS=你的服务器公网IP
```

---

## 第 4 步：初始化

```bash
# 临时把 .env 导入当前 shell（仅本次手动操作用，systemd 不需要）
set -a; source .env; set +a

# 数据库迁移
python3 manage.py migrate

# 收集静态文件（admin 后台会用）
python3 manage.py collectstatic --noinput
```

---

## 第 5 步：阿里云安全组开端口

控制台 → ECS → 安全组 → 入方向规则 → 添加：

| 协议 | 端口 | 授权对象 |
|------|-----|---------|
| TCP | 8000 | 0.0.0.0/0 |

如果系统装了 `firewalld`（CentOS 默认）：

```bash
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

Ubuntu 用 `ufw`：

```bash
ufw allow 8000/tcp
```

---

## 第 6 步：用 gunicorn 跑起来试试

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

浏览器访问 `http://你的服务器IP:8000` —— 能看到趋势页就成功了。

Ctrl+C 停掉。

---

## 第 7 步：systemd 自启动

```bash
# 复制示例 service
cp deploy/gitseeker.service /etc/systemd/system/

# 按需修改（默认假定 /opt/gitseeker，跑在 :8000）
vi /etc/systemd/system/gitseeker.service

# 启动 + 开机自启
systemctl daemon-reload
systemctl enable --now gitseeker

# 查看状态
systemctl status gitseeker
# 查看日志
journalctl -u gitseeker -f
```

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

可以做个脚本 `/opt/gitseeker/update.sh`：

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

数据库就是一个文件，定期复制即可：

```bash
cp /opt/gitseeker/db.sqlite3 ~/backups/gitseeker-$(date +%Y%m%d).sqlite3
```

或者在 UI 里 **收藏 → 导入/导出 → 导出 JSON**。

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 502 / 端口不通 | 阿里云安全组没开 / 防火墙 | 第 5 步 |
| `DisallowedHost` 报错 | `ALLOWED_HOSTS` 没填对 | 编辑 `.env` 加上 IP，`systemctl restart gitseeker` |
| `CSRF verification failed` | 跨域提交表单 | 把访问域名/IP 加到 `CSRF_TRUSTED_ORIGINS` （带 `http://`）|
| admin 后台无样式 | 没跑 `collectstatic` | 第 4 步 |
| GitHub API 限流 60/h | 没配 Token | 在网站 `/settings/` 配 GitHub PAT，限流变 5000/h |

---

## 进阶（可选）

### 想用 80 端口直接访问（不带 :8000）

把 `deploy/gitseeker.service` 里 `--bind 0.0.0.0:8000` 改成 `--bind 0.0.0.0:80`，
然后 `systemctl restart gitseeker`，安全组也改成放行 80。

注意：用 80 端口必须以 root 运行，或者用 `setcap` 给 python 二进制赋权。

### 想加 HTTPS / 上域名

那需要：
1. 域名解析到服务器 IP
2. 装 Nginx 反向代理 :8000
3. 用 certbot 申请 Let's Encrypt 证书

写起来比较长，需要再问我。

### 切到 Docker

`docker run -p 8000:8000 -v $(pwd)/db.sqlite3:/app/db.sqlite3 --env-file .env gitseeker:latest`
也可以，但要先写 Dockerfile，目前没做，需要可以再问。
