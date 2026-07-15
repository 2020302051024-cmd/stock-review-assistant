import os

import streamlit as st

from config import settings
from database.db import init_db
from services.auth_service import create_user, current_user, list_users, logout, require_login
from services.auto_push_service import get_auto_push_config, run_auto_push, save_auto_push_config
from services.deepseek_config_service import get_deepseek_config, save_deepseek_config
from services.deepseek_service import DeepSeekClient, DeepSeekError
from services.mobile_access_service import build_qr_code_url, get_public_app_url, save_public_app_url
from services.push_service import PushError, send_wechat_push
from services.settings_service import get_bool_setting, get_setting, mask_secret, set_setting
from services.market_snapshot_service import list_market_snapshots
from utils.ui import apply_app_style, render_page_header


st.set_page_config(page_title="系统设置", layout="wide")
apply_app_style()
init_db()
require_login()

render_page_header("系统设置", "配置账号、DeepSeek、微信推送和手机访问。每个账号使用自己的配置。", "⚙")

st.subheader("登录与账号")
user = current_user()
if user:
    st.write(f"当前登录：`{user['username']}`")
    if st.button("退出当前账号"):
        logout()
        st.rerun()

with st.expander("创建朋友账号"):
    st.caption("新账号会拥有独立的持仓、报告、交易日志、API 和推送配置。")
    with st.form("create_user_form"):
        new_username = st.text_input("新用户名")
        new_password = st.text_input("新密码", type="password")
        new_confirm = st.text_input("确认新密码", type="password")
        create_submitted = st.form_submit_button("创建账号", type="primary")
    if create_submitted:
        if new_password != new_confirm:
            st.error("两次密码不一致")
        else:
            try:
                create_user(new_username, new_password)
                st.success(f"账号 {new_username} 已创建。")
            except Exception as exc:
                st.error(f"创建失败：{exc}")

with st.expander("已有账号"):
    users = list_users()
    if not users:
        st.write("暂无账号。")
    else:
        for item in users:
            status = "启用" if item["is_active"] else "停用"
            st.write(f"- {item['username']}｜{status}｜创建于 {item['created_at']}")

st.subheader("DeepSeek 配置状态")
client = DeepSeekClient()
deepseek_config = get_deepseek_config()

col1, col2, col3 = st.columns(3)
col1.metric("API Key", "已配置" if client.is_configured() else "未配置")
col2.metric("模型", client.model)
col3.metric("AI 超时秒数", client.timeout)

with st.form("deepseek_config_form"):
    st.caption(f"当前 Key：{mask_secret(deepseek_config['api_key']) or '未配置'}")
    api_key = st.text_input(
        "DeepSeek API Key",
        value=deepseek_config["api_key"],
        type="password",
        help="保存后会写入本地 SQLite 数据库，不会写入代码。",
    )
    base_url = st.text_input("Base URL", value=deepseek_config["base_url"] or "https://api.deepseek.com")
    model_options = ["deepseek-v4-pro", "deepseek-chat"]
    current_model = deepseek_config["model"] if deepseek_config["model"] in model_options else "deepseek-v4-pro"
    model = st.selectbox("模型", model_options, index=model_options.index(current_model))
    thinking = st.selectbox(
        "Thinking",
        ["enabled", "disabled"],
        index=0 if deepseek_config["thinking"] == "enabled" else 1,
        help="deepseek-v4-pro 文本生成建议启用。JSON 输出会自动关闭。",
    )
    reasoning_effort = st.selectbox(
        "推理强度",
        ["high", "medium", "low"],
        index=["high", "medium", "low"].index(deepseek_config["reasoning_effort"])
        if deepseek_config["reasoning_effort"] in ["high", "medium", "low"]
        else 0,
    )
    col_timeout, col_retry = st.columns(2)
    timeout_seconds = col_timeout.number_input(
        "AI 请求超时秒数",
        min_value=15,
        max_value=180,
        value=int(deepseek_config.get("timeout_seconds", 90)),
        step=15,
        help="DeepSeek 偶尔响应慢时可调高。建议 60-120 秒。",
    )
    max_retries = col_retry.number_input(
        "失败自动重试次数",
        min_value=0,
        max_value=3,
        value=int(deepseek_config.get("max_retries", 1)),
        step=1,
        help="遇到超时、限流或临时网络错误时自动重试。建议 1 次。",
    )
    save_deepseek = st.form_submit_button("保存 DeepSeek 配置", type="primary")

if save_deepseek:
    save_deepseek_config(api_key, base_url, model, thinking, reasoning_effort, timeout_seconds, max_retries)
    st.success("DeepSeek 配置已保存。页面刷新后所有 AI 功能都会使用新配置。")

st.info(
    "给别人使用时，只需要让他在这里填自己的 DeepSeek API Key。"
    "如果不填，系统会尝试读取 .env；两者都没有时，AI 功能会提示未配置。"
)

if st.button("测试 DeepSeek 连接"):
    client = DeepSeekClient()
    try:
        with st.spinner("正在测试 DeepSeek API..."):
            text = client.generate_text("请用一句话回复：连接成功。", temperature=0)
        st.success(text)
    except DeepSeekError as exc:
        st.error(f"连接测试失败：{exc}")
    except Exception as exc:
        st.error(f"连接测试异常：{exc}")

st.divider()
st.subheader("本地信息")
st.write(f"数据库路径：`{settings.DATABASE_PATH}`")
st.write(f"当前工作目录：`{os.getcwd()}`")

st.warning(
    "本系统只用于个人复盘和辅助观察，不构成投资建议；"
    "不会自动交易，也不会直接输出买入或卖出指令。"
)

st.divider()
st.subheader("手机访问二维码")
st.caption("不在同一网络下访问，需要公网地址。可以用 Streamlit Cloud 部署，或使用 Cloudflare Tunnel / ngrok 生成公网 URL。")
public_url = st.text_input(
    "公网访问地址",
    value=get_public_app_url(),
    placeholder="例如：https://your-app.streamlit.app 或 https://xxxx.trycloudflare.com",
)
col_url_save, col_qr = st.columns([1, 1])
if col_url_save.button("保存公网地址", type="primary"):
    save_public_app_url(public_url)
    st.success("公网地址已保存。")
if public_url.strip():
    qr_url = build_qr_code_url(public_url)
    col_qr.image(qr_url, caption="手机扫码打开")
    st.write(f"访问地址：{public_url}")
else:
    st.info("这里只能生成二维码。要让手机不在同一网络下访问，必须先有公网 URL。")

st.divider()
st.subheader("微信推送配置")
st.caption("第一版支持 Server酱 / PushPlus。用于手动推送“暴雷风险 + K线风险 + 仓位风险”。")
st.info(
    "PushPlus 要先在官网获取 Token，并关注/绑定对应微信公众号。"
    "如果页面提示“推送成功”但微信没收到，通常是 Token 填错、未完成绑定、消息被公众号折叠，或 PushPlus 账号通道未开通。"
)

provider_options = ["暂不确定", "Server酱", "PushPlus"]
current_provider = get_setting("push_provider", "暂不确定")
provider = st.selectbox(
    "推送类型",
    provider_options,
    index=provider_options.index(current_provider) if current_provider in provider_options else 0,
)
token = st.text_input(
    "SendKey / PushPlus Token",
    value=get_setting("push_token", ""),
    type="password",
    help="Token 会保存在本地 SQLite 数据库中，请不要提交数据库文件。",
)
enabled = st.checkbox("启用微信推送", value=get_bool_setting("push_enabled", False))

col_save, col_test = st.columns(2)
if col_save.button("保存推送配置", type="primary"):
    set_setting("push_provider", provider)
    set_setting("push_token", token)
    set_setting("push_enabled", "true" if enabled else "false")
    st.success("推送配置已保存。")

if col_test.button("发送测试推送"):
    set_setting("push_provider", provider)
    set_setting("push_token", token)
    set_setting("push_enabled", "true" if enabled else "false")
    try:
        message = send_wechat_push("股票复盘助手测试", "这是一条微信推送测试消息。")
        st.success(message)
    except PushError as exc:
        st.error(f"测试失败：{exc}")
    except Exception as exc:
        st.error(f"测试异常：{exc}")

st.divider()
st.subheader("自动推送配置")
st.caption("这里配置自动推送内容。真正每天定时执行，需要用本机定时任务调用脚本；页面下方给出命令。")
auto_config = get_auto_push_config()
with st.form("auto_push_config_form"):
    auto_enabled = st.checkbox("启用自动推送任务", value=bool(auto_config["enabled"]))
    auto_push_time = st.text_input(
        "计划推送时间",
        value=str(auto_config["push_time"]),
        help="格式 HH:MM，例如 09:00。脚本本身不会常驻等待，需要系统定时任务在这个时间调用。",
    )
    col_auto1, col_auto2 = st.columns(2)
    auto_fetch_market_price = col_auto1.checkbox(
        "推送前获取当前行情",
        value=bool(auto_config["fetch_market_price"]),
    )
    auto_include_kline = col_auto2.checkbox(
        "推送前检查 K线风险",
        value=bool(auto_config["include_kline"]),
    )
    auto_generate_daily_review = st.checkbox(
        "同时生成每日复盘报告",
        value=bool(auto_config["generate_daily_review"]),
        help="会调用 DeepSeek，可能较慢，也可能因为模型繁忙超时。",
    )
    auto_total_assets = st.number_input(
        "账户总资产，可选",
        min_value=0.0,
        value=float(auto_config["total_assets"]),
        step=1000.0,
        help="填写后可判断总股票仓位是否超过阈值。",
    )
    save_auto_push = st.form_submit_button("保存自动推送配置", type="primary")

if save_auto_push:
    save_auto_push_config(
        auto_enabled,
        auto_push_time,
        auto_include_kline,
        auto_fetch_market_price,
        auto_generate_daily_review,
        auto_total_assets,
    )
    st.success("自动推送配置已保存。")

col_auto_test, col_auto_hint = st.columns([1, 2])
if col_auto_test.button("立即执行一次自动推送"):
    try:
        with st.spinner("正在生成风险摘要并推送..."):
            result = run_auto_push(force=True)
        if result["ok"]:
            st.success(result["message"])
        else:
            st.error(f"自动推送失败：{result['message']}")
        if result.get("report_id"):
            st.info(f"已生成每日复盘报告，ID：{result['report_id']}")
        if result.get("report_error"):
            st.warning(f"每日复盘生成失败：{result['report_error']}")
    except Exception as exc:
        st.error(f"自动推送异常：{exc}")

with col_auto_hint:
    st.write("本地定时任务可以调用这个命令：")
    st.code(
        "cd '/Users/leo/AI-Knowledge/vibe coding/stock-review-assistant' && "
        "source .venv/bin/activate && "
        "python scripts/run_auto_push.py",
        language="bash",
    )
    st.caption("如果只想立即测试一次，即使未启用自动推送，也可以在命令末尾加 `--force`。")

st.divider()
st.subheader("行情缓存")
st.caption("行情获取成功后会自动保存。网络失败时，系统使用最近缓存并明确显示缓存时间。")
snapshots = list_market_snapshots(limit=30)
if snapshots:
    st.dataframe(snapshots, width="stretch", hide_index=True)
else:
    st.info("暂无行情缓存。完成一次持仓刷新或单股分析后会自动生成。")
