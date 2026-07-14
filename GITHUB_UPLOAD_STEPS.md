# GitHub 上传步骤

这个文件夹是专门整理出来用于上传 GitHub 的干净版本。

## 1. 先在 GitHub 创建仓库

1. 打开 GitHub。
2. 点击右上角 `+`。
3. 选择 `New repository`。
4. 仓库名建议：

```text
stock-review-assistant
```

5. 建议先选 `Private` 私有仓库。
6. 不要勾选自动生成 README。
7. 点击 `Create repository`。

## 2. 在本地进入这个干净文件夹

```bash
cd "/Users/leo/AI-Knowledge/vibe coding/stock-review-assistant-github"
```

## 3. 初始化 Git

```bash
git init
git add .
git status
```

检查 `git status` 里不要出现这些文件：

```text
.env
.venv
data/stock_assistant.db
.streamlit
```

如果没有这些，就继续。

## 4. 提交代码

```bash
git commit -m "Initial stock review assistant"
```

## 5. 绑定 GitHub 仓库

把下面命令里的 `你的用户名` 改成你的 GitHub 用户名：

```bash
git branch -M main
git remote add origin https://github.com/你的用户名/stock-review-assistant.git
git push -u origin main
```

如果 GitHub 页面给了你自己的仓库地址，就用它替换上面的地址。

## 6. 上传后怎么部署到 Streamlit Cloud

1. 打开 Streamlit Community Cloud。
2. 选择 `New app`。
3. 选择你的 GitHub 仓库。
4. Main file path 填：

```text
app.py
```

5. 点击 Deploy。
6. 第一次打开网页时，系统会让你创建管理员账号。
7. 登录后去“系统设置”里填写 DeepSeek API Key。

## 7. 不要上传的文件

这些文件不应该出现在 GitHub：

```text
.env
.venv/
data/stock_assistant.db
.streamlit/
Library/
```

原因：

- `.env` 里可能有 DeepSeek API Key。
- `data/stock_assistant.db` 里有你的持仓、报告、登录账号和推送配置。
- `.venv` 是本地 Python 环境，别人不需要。

