# 草皮哥平台服务器快速启动

适用场景：已经有一台云服务器，想先让公司同事通过链接使用。

## 1. 上传项目

把打包出来的 `GrassGuy-Football-Designer-版本号.zip` 上传到服务器。

解压后进入目录：

```bash
cd GrassGuy-Football-Designer
```

## 2. 设置访问密码

复制配置文件：

```bash
cp .env.example .env
```

编辑 `.env`：

```text
GRASSGUY_APP_PASSWORD=这里改成公司内部密码
```

如果暂时不想设置密码，可以留空：

```text
GRASSGUY_APP_PASSWORD=
```

## 3. 启动服务

服务器已安装 Docker 时执行：

```bash
docker compose up -d --build
```

查看是否运行：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f
```

## 4. 先用 IP 测试

浏览器打开：

```text
http://服务器IP:8501
```

能打开后，再做域名和 HTTPS。

## 5. 推荐域名访问：Cloudflare Tunnel

这种方式不需要把服务器 `8501` 端口直接暴露到公网。

在 Cloudflare Zero Trust 后台创建 Tunnel，把公开域名指向：

```text
http://grassguy-football-designer:8501
```

然后把 Cloudflare 给出的 Token 写进 `.env`：

```text
CLOUDFLARE_TUNNEL_TOKEN=这里填写 Cloudflare Tunnel Token
```

启动：

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build
```

最终访问：

```text
https://design.caopige.com
```

## 6. 传统域名访问

推荐绑定：

```text
https://design.caopige.com
```

可以用两种方式：

- Nginx 反向代理到 `http://127.0.0.1:8501`
- Cloudflare Tunnel 转发到 `http://127.0.0.1:8501`

## 7. 更新版本

后续我在本机改完代码后，重新打包上传服务器，然后执行：

```bash
docker compose up -d --build
```

旧的 PDF 和图片会保存在 `output` 目录，不会因为容器重启丢失。
