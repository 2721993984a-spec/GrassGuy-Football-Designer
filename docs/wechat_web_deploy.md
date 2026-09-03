# 草皮哥足球场平台：微信可访问网页部署说明

目标：先把当前平台做成公司内部网页工具。公司同事在微信里打开一个 HTTPS 链接，就可以输入尺寸、生成图纸、下载 Excel 和 PDF。

## 推荐方案

第一阶段不要急着做正式微信小程序，先部署成网页：

- 前端和操作界面继续使用 Streamlit
- 计算、画图、Excel、PDF 逻辑继续使用现在的 Python 代码
- 部署到云服务器
- 配一个公司域名和 HTTPS
- 把链接发到微信群或做成企业微信工作台入口

这个方式最快，现有功能可以直接复用。

## 三种可分享方式

### 方案 A：公司电脑局域网使用

适合办公室内部临时用。把工具运行在一台固定电脑上，同一个 WiFi 或局域网里的同事访问这台电脑的内网 IP。

优点：

- 最快，不需要买服务器
- 适合内部先试用

限制：

- 离开公司网络后不能访问
- 开工具的电脑不能关机
- 手机访问体验依赖公司网络

### 方案 B：云服务器网页工具（当前推荐）

把当前 Streamlit 工具部署到云服务器，绑定 HTTPS 域名，例如：

```text
https://design.caopige.com
```

同事电脑、手机、微信、企业微信都可以直接打开。

优点：

- 现有 Python 代码基本不用重写
- PDF、图片、用量计算逻辑可以全部保留
- 上线快，后续也能继续迭代

限制：

- 需要一台云服务器
- 如果使用国内服务器，域名通常需要备案
- 建议增加简单登录，避免外部人员随便访问

### 方案 C：正式微信小程序

等网页版本稳定后，再做真正微信小程序。正式小程序不是把 Streamlit 直接打包进去，而是需要拆成：

- 微信小程序前端：输入参数、查看图纸、下载文件
- Python 后端 API：负责计算、画图、导出 PDF
- 文件存储：保存 PNG、PDF、Excel
- 员工登录：限制公司内部使用

优点：

- 手机体验最好
- 可以放到微信小程序列表里
- 后期适合做项目历史、员工账号、客户方案库

限制：

- 开发量比网页大很多
- 需要微信小程序账号、认证、服务器域名、HTTPS、审核
- 当前 Streamlit 页面需要重做成小程序页面

## 当前建议执行顺序

1. 先用方案 B，把当前工具部署成公司专用 HTTPS 网页。
2. 手机端先按“小程序式网页”优化：界面简洁、按钮大、下载位置清楚。
3. 给同事试用 1-2 周，记录真实问题。
4. 稳定后再决定是否做正式微信小程序。

如果只是让公司同事尽快使用，方案 B 是最合适的第一步。

## 需要准备

- 一台云服务器，推荐 2 核 4G 起步
- 一个域名，例如 `design.caopige.com`
- 域名备案，国内服务器通常需要
- HTTPS 证书，可以用云厂商免费证书或 Let's Encrypt
- 服务器安装 Docker 和 Docker Compose

## Docker 部署

进入项目目录：

```bash
cd GrassGuy-Football-Designer
```

构建并启动：

```bash
docker compose up -d --build
```

查看运行状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f
```

浏览器访问：

```text
http://服务器IP:8501
```

## 配 HTTPS 域名

建议用 Nginx 反向代理，把外部 HTTPS 域名转到本机 `8501` 端口。

Nginx 示例：

```nginx
server {
    listen 80;
    server_name design.caopige.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name design.caopige.com;

    ssl_certificate /etc/nginx/ssl/design.caopige.com.pem;
    ssl_certificate_key /etc/nginx/ssl/design.caopige.com.key;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

配置完成后访问：

```text
https://design.caopige.com
```

## 公司同事使用方式

- 把 HTTPS 链接发到微信群
- 同事在微信里直接打开
- 输入项目名称、客户名称、场地尺寸
- 点击生成
- 预览尺寸图、效果图、施工图
- 下载 PDF 或 Excel

## 输出文件保存位置

服务器上输出文件会保存在：

- `output/images/`
- `output/pdf/`
- `output/excel/`

Docker 部署时这些目录已经挂载到项目本地目录，重启容器不会丢。

## 后续升级到正式微信小程序

等网页版本稳定后，可以再拆成正式小程序：

- 小程序前端：输入参数、查看图片、下载文件
- Python 后端：提供 API，继续负责计算、画图、导出
- 文件服务：保存 PNG、PDF、Excel
- 用户系统：员工登录、项目历史记录、客户方案管理

建议先让网页版本跑 1-2 周，收集公司同事实际反馈，再决定小程序页面和功能。
