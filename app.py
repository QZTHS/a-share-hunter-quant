import streamlit as st
import pandas as pd
from datetime import datetime
import time
import random
from requests.exceptions import ConnectionError, RequestException, Timeout

st.set_page_config(
    page_title="A股猎手 Quant 1.1",
    page_icon="📈",
    layout="wide"
)

st.title("📈 A股猎手 Quant 1.1")
st.caption("日线研究原型｜真实数据连接测试版｜不提供自动交易")
st.warning(
    "第三方行情可能延迟、缺失或临时不可用。"
    "本版先验证行情连接和基础筛选，尚未完成完整历史回测。"
)

# -------------------------------------------------
# 工具函数：带重试的东方财富实时行情
# -------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def get_spot(max_retries: int = 5):
    """获取A股实时行情（带指数退避重试）"""
    import akshare as ak

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # 指数退避 + 随机抖动，降低被限流概率
                sleep_sec = min(2 ** attempt + random.uniform(0.3, 1.2), 12)
                time.sleep(sleep_sec)

            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                raise RuntimeError("行情接口返回空数据")
            return df

        except (ConnectionError, RequestException, Timeout, Exception) as e:
            last_error = e
            # 最后一次仍然失败则抛出
            if attempt == max_retries - 1:
                raise last_error
    raise last_error

# -------------------------------------------------
# 工具函数：带重试的历史日线
# -------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_hist(code: str, start_date: str, end_date: str, adjust: str, max_retries: int = 4):
    """获取个股历史日线（带重试）"""
    import akshare as ak

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(1.5 * attempt + random.uniform(0.2, 0.8))

            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            return df

        except (ConnectionError, RequestException, Timeout, Exception) as e:
            last_error = e
            if attempt == max_retries - 1:
                raise last_error
    raise last_error

# -------------------------------------------------
# 侧边栏
# -------------------------------------------------
with st.sidebar:
    st.header("研究设置")
    strategy = st.selectbox(
        "策略方向",
        ["超短线观察", "短波段观察", "中线趋势观察"]
    )
    min_pct = st.slider("最低当日涨幅（%）", -10.0, 10.0, 2.0, 0.5)
    min_amount = st.number_input(
        "最低成交额（万元）",
        min_value=0,
        value=10000,
        step=5000
    )

    st.divider()
    if st.button("清除缓存并刷新", type="secondary"):
        st.cache_data.clear()
        st.rerun()

    # 显示 akshare 版本，方便排查
    try:
        import akshare as ak
        st.caption(f"akshare 版本：{ak.__version__}")
    except Exception:
        st.caption("akshare 未正确安装")

# -------------------------------------------------
# 一、真实行情连接
# -------------------------------------------------
st.subheader("一、真实行情连接")

try:
    with st.spinner("正在尝试获取A股行情（含自动重试）……"):
        spot = get_spot()
    st.success(f"行情接口连接成功：获取到 {len(spot):,} 条行情记录。")
    st.caption(
        "获取时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        + "（服务器时间；行情本身可能延迟）"
    )
except Exception as e:
    st.error("暂时无法获取真实行情，系统不会用模拟数据替代。")
    st.write("可能原因：第三方接口限流、网络不可达（海外服务器常见）、接口变更或部署环境问题。")
    st.code(f"{type(e).__name__}: {str(e)[:800]}")
    st.info(
        "建议：\n"
        "1. 点击左侧「清除缓存并刷新」再试几次\n"
        "2. 本地（尤其是国内网络）运行成功率远高于 Streamlit Cloud\n"
        "3. 升级 akshare：pip install -U akshare"
    )
    st.stop()

# -------------------------------------------------
# 字段检查与预处理
# -------------------------------------------------
need = ["代码", "名称", "最新价", "涨跌幅", "成交额"]
missing = [c for c in need if c not in spot.columns]
if missing:
    st.error(f"接口字段不符合预期，缺少：{missing}")
    st.write("实际字段：", list(spot.columns))
    st.stop()

for c in ["最新价", "涨跌幅", "成交额", "换手率", "量比", "振幅"]:
    if c in spot.columns:
        spot[c] = pd.to_numeric(spot[c], errors="coerce")

spot["代码"] = spot["代码"].astype(str).str.zfill(6)
# 过滤常见A股代码（沪深主板、创业板、科创板、北交所部分）
spot = spot[spot["代码"].str.match(r"^(60|68|00|30|83|87|43)")].copy()

up = int((spot["涨跌幅"] > 0).sum())
down = int((spot["涨跌幅"] < 0).sum())
flat = int((spot["涨跌幅"] == 0).sum())
amount_yi = spot["成交额"].sum(skipna=True) / 1e8

a, b, c, d = st.columns(4)
a.metric("纳入统计证券", f"{len(spot):,}")
b.metric("上涨 / 下跌", f"{up:,} / {down:,}")
c.metric("平盘", f"{flat:,}")
d.metric("样本成交额合计", f"{amount_yi:.0f}亿元")

# -------------------------------------------------
# 三个标签页
# -------------------------------------------------
tabs = st.tabs(["市场概览", "策略候选", "个股日线分析"])

with tabs[0]:
    cols = [x for x in ["代码", "名称", "最新价", "涨跌幅", "成交额", "换手率", "量比"] if x in spot.columns]
    left, right = st.columns(2)
    with left:
        st.markdown("#### 涨幅前20")
        st.dataframe(
            spot.sort_values("涨跌幅", ascending=False)[cols].head(20),
            use_container_width=True,
            hide_index=True
        )
    with right:
        st
