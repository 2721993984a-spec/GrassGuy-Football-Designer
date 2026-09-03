# 草皮哥平台上线分享清单

目标：把当前工具做成公司同事电脑和手机都能打开的内部网页。

## 推荐上线方式

第一版用“公司专用网页”上线，不直接重写微信小程序。默认建议使用“云服务器 + Docker + Cloudflare Tunnel”。

正式访问形式：

```text
https://design.caopige.com
```

同事可以：

- 电脑浏览器打开
- 手机浏览器打开
- 微信或企业微信里打开
- 手机添加到桌面，当成接近小程序的入口使用

## 服务器准备

建议配置：

- 2核 4G 云服务器起步
- Ubuntu 22.04 或类似 Linux 系统
- Docker 和 Docker Compose
- 一个域名，例如 `design.caopige.com`
- HTTPS 证书或 Cloudflare 代理

## 部署步骤

1. 把 `GrassGuy-Football-Designer` 文件夹上传到服务器。
2. 进入项目目录。
3. 复制环境变量文件：

```bash
cp .env.example .env
```

4. 修改 `.env` 里的密码：

```text
GRASSGUY_APP_PASSWORD=公司内部密码
```

5. 启动服务：

```bash
docker compose up -d --build
```

6. 先用服务器 IP 测试：

```text
http://服务器IP:8501
```

7. 再绑定 HTTPS 域名。

## Cloudflare Tunnel 方式

如果暂时不想开放服务器 8501 端口，可以使用 Cloudflare Tunnel。

在 Cloudflare Zero Trust 后台创建 Tunnel，并把公开域名转发到容器服务：

```text
http://grassguy-football-designer:8501
```

把 Cloudflare 给出的 Tunnel Token 写入服务器 `.env`：

```text
CLOUDFLARE_TUNNEL_TOKEN=这里填写 Cloudflare Tunnel Token
```

启动：

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build
```

最终同事访问：

```text
https://design.caopige.com
```

## 手机小程序式使用

当前阶段推荐这样做：

1. 微信里打开公司链接。
2. 点击右上角菜单。
3. 选择“在浏览器打开”或“添加到桌面”。
4. 手机桌面会有一个入口，体验接近小程序。

真正微信小程序后续再做，届时需要重新开发小程序前端，并调用现在的 Python 后端接口。

## 上线前检查

- 页面能打开
- 手机能输入尺寸
- 生成图纸不报错
- PDF 能下载
- 访问密码生效
- output 目录已挂载，重启后文件不丢
- 域名是 HTTPS

## 后续再升级

- 员工账号登录
- 项目历史记录
- 客户方案库
- 手机端专用页面
- 正式微信小程序
