# 草皮哥平台免费分享上线步骤

目标：先把当前平台做成一个可以分享的网页链接，同事电脑和手机都能打开。后续再用微信小程序 `web-view` 套这个网页。

## 第一步：准备账号

需要两个账号：

- GitHub 账号：用来放平台代码。
- Streamlit Community Cloud 账号：用 GitHub 登录即可。

## 第二步：创建 GitHub 仓库

1. 打开 `https://github.com/new`。
2. Repository name 填：

```text
GrassGuy-Football-Designer
```

3. 仓库建议先选 `Private`。
4. 不要勾选自动生成 README。
5. 点击 `Create repository`。

## 第三步：上传代码

上传本项目的上线压缩包，或者上传项目文件夹里的代码。

必须上传：

```text
app.py
requirements.txt
.streamlit/
assets/
config/
src/
docs/
knowledge/
reference_templates/
template_knowledge/
```

不要上传：

```text
logs/
output/
PDF图纸/
release_packages/
.env
.streamlit/secrets.toml
```

## 第四步：部署到 Streamlit Cloud

1. 打开 `https://share.streamlit.io`。
2. 用 GitHub 登录。
3. 点击 `Create app`。
4. 选择刚才的仓库。
5. Branch 选 `main`。
6. Main file path 填：

```text
app.py
```

7. 点击 `Deploy`。

成功后会得到一个链接，类似：

```text
https://grassguy-football-designer.streamlit.app
```

这个链接可以直接发给同事。

## 第五步：设置公司访问密码

在 Streamlit Cloud 的 App settings 里找到 Secrets，填写：

```toml
GRASSGUY_APP_PASSWORD = "这里改成公司内部密码"
```

保存后重启应用。同事打开链接时，需要输入这个密码。

## 第六步：手机使用方式

同事可以：

- 电脑浏览器打开链接。
- 手机浏览器打开链接。
- 微信里打开链接。
- 手机浏览器里添加到桌面，当成小程序入口使用。

## 后续做成正式微信小程序

正式小程序建议等网页版稳定后再做。第一版小程序可以只做一个页面，用 `web-view` 打开上面的网页链接。

正式发布微信小程序时通常还需要：

- 公司主体小程序账号。
- 备案域名。
- HTTPS。
- 在微信公众平台配置业务域名。
- 把微信校验文件放到网站根目录。

如果没有备案域名，先不要急着做正式小程序，先用网页链接给同事试用。
