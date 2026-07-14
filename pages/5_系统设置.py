import os

import streamlit as st

from config import settings
from database.db import init_db
from services.auth_service import create_user, current_user, list_users, logout, require_login
from services.deepseek_config_service import get_deepseek_config, save_deepseek_config
from services.deepseek_service import DeepSeekClient, DeepSeekError
from services.mobile_access_service import build_qr_code_url, get_public_app_url, save_public_app_url
from services.push_service import PushError, send_wechat_push
from services.settings_service import get_bool_setting, get_setting, mask_secret, set_setting


st.set_page_config(page_title="系统设置", layout="wide")
init_db()
require_login()

st.title("⚙️ 系统设置")
st.caption("在页面里配置 DeepSeek 和微信推送。普通用户不需要手动编辑终端或 .env。")

st.subheader("🔐 登录与账号")
user = current_user()
if user:
    st.write(f"当前登录：`{user['username']}`")
    if st.button("退出当前账号"):
        logout()
        st.rerun()

with st.expander("创建朋友账号"):
    st.caption("当前版本是登录保护，不是数据隔离。多个账号登录后看到的是同一套持仓和报告。")
    with st.form("create_user_form"):
        new_username = st.text_input("新用户名")
        new_password = st.text_input("新密码", type="password")
        new_confirm = st.text_input("确认新密码", type="password")
        create_submitted = st.form_submit_button("创建账号")
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

st.subheader("🧠 DeepSeek 配置状态")
client = DeepSeekClient()
deepseek_config = get_deepseek_config()

col1, col2, col3 = st.columns(3)
col1.metric("API Key", "已配置" if client.is_configured() else "未配置")
col2.metric("模型", client.model)
col3.metric("超时秒数", settings.REQUEST_TIMEOUT_SECONDS)

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
    save_deepseek = st.form_submit_button("保存 DeepSeek 配置")

if save_deepseek:
    save_deepseek_config(api_key, base_url, model, thinking, reasoning_effort)
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
st.subheader("💾 本地信息")
st.write(f"数据库路径：`{settings.DATABASE_PATH}`")
st.write(f"当前工作目录：`{os.getcwd()}`")

st.warning(
    "本系统只用于个人复盘和辅助观察，不构成投资建议；"
    "不会自动交易，也不会直接输出买入或卖出指令。"
)

st.divider()
st.subheader("📱 手机访问二维码")
st.caption("不在同一网络下访问，需要公网地址。可以用 Streamlit Cloud 部署，或使用 Cloudflare Tunnel / ngrok 生成公网 URL。")
public_url = st.text_input(
    "公网访问地址",
    value=get_public_app_url(),
    placeholder="例如：https://your-app.streamlit.app 或 https://xxxx.trycloudflare.com",
)
col_url_save, col_qr = st.columns([1, 1])
if col_url_save.button("保存公网地址"):
    save_public_app_url(public_url)
    st.success("公网地址已保存。")
if public_url.strip():
    qr_url = build_qr_code_url(public_url)
    col_qr.image(qr_url, caption="手机扫码打开")
    st.write(f"访问地址：{public_url}")
else:
    st.info("这里只能生成二维码。要让手机不在同一网络下访问，必须先有公网 URL。")

st.divider()
st.subheader("📤 微信推送配置")
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
if col_save.button("保存推送配置"):
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
