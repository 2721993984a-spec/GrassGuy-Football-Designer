# GrassGuy-Football-Designer

草皮哥足球场智能设计方案平台。

这是一个内部使用的足球场草坪设计出图工具，可以输入场地类型、长宽、缓冲区、条纹宽度和标线参数，一键生成：

- 尺寸图
- 彩色效果图
- 简易施工图
- 草坪用量表
- 辅材用量表
- Excel 用量表
- PDF 方案

第一版定位是销售方案图和施工参考图，不作为最终专业施工蓝图。

## 本地运行

进入项目目录：

```powershell
cd GrassGuy-Football-Designer
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动平台：

```powershell
python -m streamlit run app.py
```

浏览器打开：

```text
http://127.0.0.1:8501
```

## 公司多人使用

推荐先做成“微信里可打开的网页工具”：

1. 把项目部署到云服务器
2. 配置公司域名和 HTTPS
3. 把链接发到微信群或企业微信
4. 同事在微信里直接打开使用

详细部署说明见：

```text
docs/wechat_web_deploy.md
```

上线执行清单见：

```text
docs/share_online_checklist.md
```

服务器快速启动见：

```text
docs/server_quick_start.md
```

免费试用部署见：

```text
docs/streamlit_cloud_deploy.md
```

最简单的免费上线和小程序套壳步骤见：

```text
docs/free_online_and_miniprogram_steps.md
```

如需限制外部访问，可以配置访问密码：

```powershell
$env:GRASSGUY_APP_PASSWORD="公司内部密码"
python -m streamlit run app.py
```

Docker 部署时复制 `.env.example` 为 `.env`，然后修改里面的 `GRASSGUY_APP_PASSWORD`。

推荐线上分享方式：云服务器 + Docker + Cloudflare Tunnel。

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml up -d --build
```

生成上线包：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1
```

生成的 zip 在：

```text
release_packages/
```

## Docker 部署

服务器安装 Docker 后，在项目目录运行：

```bash
docker compose up -d --build
```

访问：

```text
http://服务器IP:8501
```

正式给同事用时，建议再配 HTTPS 域名，例如：

```text
https://design.caopige.com
```

## 输出位置

所有生成文件保存在 `output` 目录：

- 图片：`output/images/`
- Excel：`output/excel/`
- PDF：`output/pdf/`

文件名重复时系统会自动加时间戳，不会覆盖旧文件。

## 当前规则

- 固定深浅绿条纹
- 支持 2 米深浅或 4 米深浅
- 中线位于浅色条纹中心，再向两侧依次深浅交替
- 缓冲区颜色与场地条纹保持一致
- 标线固定白色
- 辅材只保留胶水和接缝布
- 尺寸图按模板简洁标注

## 后续升级方向

- 增加项目历史记录
- 增加账号登录和员工权限
- 增加客户方案库
- 增加在线分享 PDF 链接
- 后续可重构成正式微信小程序：小程序前端 + Python 后端 API
