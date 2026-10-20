import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date

st.set_page_config(page_title="A股猎手 Quant 1.0", page_icon="📈", layout="wide")

st.title("📈 A股猎手 Quant 1.0")
st.caption("个人研究工具 · 日线版原型 | 当前未连接真实行情，不构成投资建议")

with st.sidebar:
    st.header("系统设置")
    mode = st.radio("数据模式", ["原型演示（模拟数据）", "真实数据（尚未配置）"])
    st.info("演示模式中的股票、价格、涨跌幅均为模拟数据，不可用于真实交易决策。")
    st.divider()
    st.subheader("策略类型")
    strategy = st.selectbox("选择策略", ["超短线（1–5日）", "短波段（5–20日）", "中线趋势（20–60日）"])
    min_score = st.slider("最低综合评分", 0, 100, 60)
    st.caption("后续接入真实行情后，这些参数将用于全市场筛选。")

if mode == "真实数据（尚未配置）":
    st.warning("真实行情接口尚未配置。为避免误导，当前不展示任何实时或真实市场数据。")
    st.markdown("""
    ### 下一步需要完成
    1. 选择并验证日线行情数据源；
    2. 配置数据接口与缓存；
    3. 加入A股代码列表、停复牌与涨跌停处理；
    4. 完成无未来函数的回测。
    """)
    st.stop()

# Clearly synthetic sample data for UI prototyping only.
rng = np.random.default_rng(42)
names = ["示例科技A", "示例设备B", "示例软件C", "示例材料D", "示例通信E",
         "示例医药F", "示例消费G", "示例电力H", "示例制造I", "示例云计算J",
         "示例电子K", "示例传媒L", "示例机械M", "示例汽车N", "示例化工O"]
codes = [f"SIM{i:03d}" for i in range(1, len(names)+1)]
returns = rng.normal(1.0, 3.2, len(names)).round(2)
vol_ratio = rng.uniform(0.7, 2.6, len(names)).round(2)
rs20 = rng.uniform(-8, 18, len(names)).round(2)
trend = rng.integers(35, 96, len(names))
scores = np.clip(0.35 * (returns + 5) * 5 + 0.25 * vol_ratio * 20 + 0.2 * (rs20 + 8) * 3 + 0.2 * trend, 0, 100).round(1)

df = pd.DataFrame({
    "代码（模拟）": codes,
    "名称（模拟）": names,
    "当日涨跌幅%（模拟）": returns,
    "量比（模拟）": vol_ratio,
    "20日相对强度（模拟）": rs20,
    "趋势分（模拟）": trend,
    "综合评分（演示）": scores
}).sort_values("综合评分（演示）", ascending=False)

# Header metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("数据状态", "演示数据")
c2.metric("策略", strategy)
c3.metric("候选样本", len(df))
c4.metric("评分门槛", f"{min_score}/100")

st.warning("以下全部为界面演示用模拟数据，股票名称与代码不是实际证券，不可据此买卖。")

tab1, tab2, tab3, tab4 = st.tabs(["市场总览", "策略选股", "个股分析", "回测与风险"])

with tab1:
    st.subheader("市场状态面板（演示）")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("市场广度", "示例 56%", help="模拟值")
    m2.metric("强势样本占比", "示例 18%", help="模拟值")
    m3.metric("成交额变化", "示例 +7.2%", help="模拟值")
    m4.metric("风险状态", "待真实数据验证")
    chart_df = df.sort_values("当日涨跌幅%（模拟）")
    fig = px.bar(chart_df, x="名称（模拟）", y="当日涨跌幅%（模拟）", title="样本涨跌幅（模拟）")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("真实版本会加入指数趋势、涨跌家数、成交额、涨停/跌停与行业轮动等指标（视数据源覆盖情况而定）。")

with tab2:
    st.subheader("策略候选池（演示）")
    filtered = df[df["综合评分（演示）"] >= min_score]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button("下载当前演示表 CSV", filtered.to_csv(index=False).encode("utf-8-sig"),
                       file_name="demo_screening.csv", mime="text/csv")
    st.markdown("**后续规则方向**")
    if strategy.startswith("超短线"):
        st.write("- 1/3/5日动量、成交额变化、量价配合、市场情绪与板块强度。")
    elif strategy.startswith("短波段"):
        st.write("- 20/60日趋势、平台突破、放量突破、缩量回踩、行业相对强度。")
    else:
        st.write("- 营收/利润/现金流、估值区间、趋势结构、行业景气与催化因素。")

with tab3:
    st.subheader("个股研究卡（演示）")
    chosen = st.selectbox("选择一个模拟样本", df["名称（模拟）"].tolist())
    row = df[df["名称（模拟）"] == chosen].iloc[0]
    a, b, c = st.columns(3)
    a.metric("综合评分", f"{row['综合评分（演示）']}/100")
    b.metric("当日涨跌幅", f"{row['当日涨跌幅%（模拟）']}%")
    c.metric("量比", f"{row['量比（模拟）']}x")
    st.markdown("#### 入选理由（示例规则）")
    reasons = []
    if row["当日涨跌幅%（模拟）"] > 2: reasons.append("当日动量较强（模拟）")
    if row["量比（模拟）"] > 1.5: reasons.append("成交活跃度较高（模拟）")
    if row["20日相对强度（模拟）"] > 5: reasons.append("20日相对强度较高（模拟）")
    if row["趋势分（模拟）"] > 70: reasons.append("趋势评分较高（模拟）")
    st.write("；".join(reasons) if reasons else "当前样本未触发明显强势条件（模拟）")
    st.markdown("#### 失效条件（正式版将量化）")
    st.write("- 突破失败且放量下跌；- 行业强度转弱；- 跌破策略定义的趋势/止损条件。")
    st.caption("这只是演示卡片。正式版将显示真实行情、关键价位、基本面披露日期及数据来源。")

with tab4:
    st.subheader("回测模块（尚未接入）")
    st.info("当前不生成虚构回测收益。正式版将先定义买入/卖出规则，再纳入交易费用、滑点、涨跌停无法成交、停牌和财报披露时点。")
    st.markdown("""
    **计划输出**
    - 总收益与年化收益
    - 最大回撤、波动率、夏普比率
    - 胜率、盈亏比、平均持仓天数
    - 与沪深300等基准比较
    - 分年份、分行情环境与分行业表现
    """)

st.divider()
st.caption(f"原型版本 · 页面生成日期：{date.today().isoformat()} · 下一阶段：接入并验证真实日线数据。")
