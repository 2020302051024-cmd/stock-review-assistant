# 股票复盘助手

个人自用的股票复盘与辅助决策系统 MVP。系统不会自动交易，也不会直接给出“买入/卖出”指令，只提供带依据和风险提示的复盘、观察建议与新手解释。

## 当前阶段

当前已包含第 1-4 阶段能力：

- 基础项目结构
- Python 依赖清单
- 环境变量模板
- 配置读取
- SQLite 数据库初始化代码
- Streamlit 首页仪表盘
- 持仓新增、修改、删除、查看
- 自动或手动当前价盈亏计算
- A股 akshare 行情入口
- 港股 / 美股 yfinance 行情入口
- MA5 / MA10 / MA20 / MA60 / MACD / RSI 等基础技术指标
- 单只股票 K 线辅助分析
- DeepSeek API 封装
- 财报、公告、新闻粘贴摘要
- 每日复盘报告生成
- 历史 AI 报告保存
- 系统设置和 API 连接测试页面
- 基础登录保护和朋友账号创建

## 技术栈

- Python
- Streamlit
- SQLite
- pandas
- requests
- akshare
- yfinance
- python-dotenv
- DeepSeek OpenAI 兼容接口

## 安装

```bash
cd stock-review-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

普通用户可以直接在应用页面里配置 DeepSeek：

1. 启动应用
2. 首次打开时创建管理员账号
3. 登录后打开“系统设置”
4. 填写 DeepSeek API Key
5. 保存并测试连接

也可以复制环境变量模板：

```bash
cp .env.example .env
```

然后在 `.env` 中填写：

```bash
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

## 初始化数据库

```bash
python database/db.py
```

默认数据库路径：

```text
data/stock_assistant.db
```

## 启动应用

```bash
streamlit run app.py
```

## 当前页面

- 首页风险面板：优先查看暴雷风险、K线风险、仓位风险和行业集中度
- 持仓管理：维护股票代码、名称、买入价、数量、买入日期、市场和备注
- 单只股票分析：获取日K数据，计算均线、MACD、RSI、成交量变化和风险信号
- 财报公告分析：支持单篇摘要，也支持按持仓行业和关注领域生成每日消息面汇总
- 系统设置：可配置公网访问地址并生成手机扫码二维码
- 每日复盘报告：基于持仓、盈亏和技术面生成复盘报告
- 系统设置：查看 DeepSeek 配置状态并测试连接

详细使用说明见 [USAGE.md](USAGE.md)。

## MVP 阶段规划

1. 生成项目结构、依赖、配置和数据库初始化代码：已完成
2. 实现持仓管理功能：已完成
3. 实现行情数据获取和盈亏计算：已完成
4. 实现技术指标计算和单只股票分析：已完成
5. 接入 DeepSeek API，生成财报摘要和每日复盘报告：已完成
6. 完善 Streamlit 多页面界面：已完成

## DeepSeek 封装能力

`services/deepseek_service.py` 提供 `DeepSeekClient`：

- `generate_text()`：普通文本生成
- `generate_json()`：结构化 JSON 输出
- API Key 从环境变量读取，不写死在代码里
- 支持超时配置
- 对超时、HTTP 错误、返回结构异常提供友好错误

## 数据安全

`.env`、本地虚拟环境、Python 缓存和 SQLite 数据库已加入 `.gitignore`。请不要把真实 API Key 提交到 Git 仓库或公开聊天记录中。

## 风险提示

本系统只用于个人复盘和辅助观察，不构成投资建议，不自动交易，也不直接输出买入或卖出指令。技术指标存在滞后性，行情数据也可能因第三方接口限制而失败或延迟。
