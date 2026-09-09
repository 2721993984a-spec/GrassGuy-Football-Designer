# Streamlit Community Cloud 免费部署说明

目标：先用免费方式生成一个公网链接，让同事电脑和手机都能打开试用。

## 适用情况

这个方案适合第一阶段试用：

- 不买服务器
- 电脑和手机都能通过链接打开
- 保留当前 Streamlit 页面、计算、画图、PDF 导出
- 可以设置一个简单访问密码

注意：

- 免费平台不适合作为长期稳定生产环境
- 生成的文件不建议当长期云盘保存
- 国内微信访问速度可能受网络影响

## 需要准备

- GitHub 账号
- Streamlit Community Cloud 账号
- 一个 GitHub 仓库，建议先设为 Private

## GitHub 仓库文件

上传项目根目录里的这些文件和目录：

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
.env
logs/
output/
PDF图纸/
release_packages/
```

## Streamlit Cloud 部署

1. 打开 Streamlit Community Cloud。
2. 用 GitHub 登录。
3. 选择刚才的 GitHub 仓库。
4. Branch 选择 `main`。
5. Main file path 填：

```text
app.py
```

6. 点击 Deploy。

## 设置访问密码

在 Streamlit Cloud 的 App Settings 里找到 Secrets，添加：

```toml
GRASSGUY_APP_PASSWORD = "公司内部密码"
```

不设置这个值时，平台会免登录打开。

## 同事使用方式

部署成功后会得到一个类似下面的链接：

```text
https://你的应用名.streamlit.app
```

把链接发到微信群或企业微信，同事就可以直接打开。

## 后续更新

本机改完代码后：

1. 重新上传或推送到 GitHub。
2. Streamlit Cloud 会自动重新部署。
3. 同事刷新链接即可看到新版。
