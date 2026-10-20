import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="A股猎手 Quant 1.1", page_icon="📈", layout="wide")
st.title("📈 A股猎手 Quant 1.1")
st.caption("日线研究原型｜真实数据连接测试版｜不提供自动交易")
st.warning("第三方行情可能延迟、缺失或临时不可用。本版先验证行情连接和基础筛选，尚未完成完整历史回测。")

@st.cache_data(ttl=900, show_spinner=False)
def get_spot():
    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    if df is None or df.empty:
        raise RuntimeError("行情接口返回空数据")
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def get_hist(code, start_date, end_date, adjust):
    import akshare as ak
    return ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)

with st.sidebar:
    st.header("研究设置")
    strategy = st.selectbox("策略方向", ["超短线观察", "短波段观察", "中线趋势观察"])
    min_pct = st.slider("最低当日涨幅（%）", -10.0, 10.0, 2.0, 0.5)
    min_amount = st.number_input("最低成交额（万元）", min_value=0, value=10000, step=5000)
    if st.button("清除缓存并刷新"):
        st.cache_data.clear()
        st.rerun()

st.subheader("一、真实行情连接")
try:
    with st.spinner("正在尝试获取A股行情……"):
        spot = get_spot()
    st.success(f"行情接口连接成功：获取到 {len(spot):,} 条行情记录。")
    st.caption("获取时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "（服务器时间；行情本身可能延迟）")
except Exception as e:
    st.error("暂时无法获取真实行情，系统不会用模拟数据替代。")
    st.write("可能原因：第三方接口限流、网络不可达、接口变更或部署环境问题。")
    st.code(f"{type(e).__name__}: {str(e)[:600]}")
    st.stop()

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
spot = spot[spot["代码"].str.match(r"^(60|68|00|30|83|87|43)")].copy()
up = int((spot["涨跌幅"] > 0).sum())
down = int((spot["涨跌幅"] < 0).sum())
flat = int((spot["涨跌幅"] == 0).sum())
amount_yi = spot["成交额"].sum(skipna=True) / 1e8
a,b,c,d = st.columns(4)
a.metric("纳入统计证券", f"{len(spot):,}")
b.metric("上涨 / 下跌", f"{up:,} / {down:,}")
c.metric("平盘", f"{flat:,}")
d.metric("样本成交额合计", f"{amount_yi:.0f}亿元")

tabs = st.tabs(["市场概览", "策略候选", "个股日线分析"])
with tabs[0]:
    cols = [x for x in ["代码","名称","最新价","涨跌幅","成交额","换手率","量比"] if x in spot.columns]
    left,right = st.columns(2)
    with left:
        st.markdown("#### 涨幅前20")
        st.dataframe(spot.sort_values("涨跌幅",ascending=False)[cols].head(20), use_container_width=True, hide_index=True)
    with right:
        st.markdown("#### 成交额前20")
        st.dataframe(spot.sort_values("成交额",ascending=False)[cols].head(20), use_container_width=True, hide_index=True)
    bins=[-100,-9,-7,-5,-3,-1,0,1,3,5,7,9,11,100]
    labels=["≤-9%","-9~-7%","-7~-5%","-5~-3%","-3~-1%","-1~0%","0~1%","1~3%","3~5%","5~7%","7~9%","9~11%",">11%"]
    dist=pd.cut(spot["涨跌幅"],bins=bins,labels=labels,right=False).value_counts(sort=False)
    st.markdown("#### 市场涨跌分布")
    st.bar_chart(dist)

with tabs[1]:
    st.markdown(f"#### {strategy}｜基础候选")
    filt=spot[(spot["涨跌幅"]>=min_pct)&(spot["成交额"]>=min_amount*10000)].copy()
    if "量比" in filt.columns and strategy != "中线趋势观察":
        filt=filt[filt["量比"].isna() | (filt["量比"]>=1.0)]
    filt["筛选说明"] = {
        "超短线观察":"当日涨幅、成交额、量比初筛；未结合连板和板块情绪",
        "短波段观察":"当日强势和成交活跃初筛；需继续验证20/60日平台与回踩",
        "中线趋势观察":"仅为流动性和当日强度初筛；未纳入财务质量和估值"
    }[strategy]
    cols=[x for x in ["代码","名称","最新价","涨跌幅","成交额","换手率","量比","筛选说明"] if x in filt.columns]
    st.write(f"符合基础条件：**{len(filt):,}** 只")
    st.dataframe(filt.sort_values(["涨跌幅","成交额"],ascending=False)[cols].head(300),use_container_width=True,hide_index=True)
    st.download_button("下载候选名单 CSV",filt[cols].to_csv(index=False).encode("utf-8-sig"),"a_share_candidates.csv","text/csv")
    st.caption("这只是当日行情初筛，不是经过历史验证的交易策略。")

with tabs[2]:
    opts=spot[["代码","名称"]].drop_duplicates().sort_values("代码")
    selected=st.selectbox("选择股票",opts.apply(lambda r:f"{r['代码']}｜{r['名称']}",axis=1).tolist())
    code=selected.split("｜")[0]
    adj=st.selectbox("复权方式",["前复权","不复权","后复权"])
    adjmap={"前复权":"qfq","不复权":"","后复权":"hfq"}
    if st.button("获取近一年日线",type="primary"):
        end=datetime.now().strftime("%Y%m%d")
        start=(pd.Timestamp.today()-pd.Timedelta(days=400)).strftime("%Y%m%d")
        try:
            with st.spinner("获取历史日线中……"):
                hist=get_hist(code,start,end,adjmap[adj])
            if hist is None or hist.empty:
                st.warning("历史行情为空。")
            else:
                for col in ["收盘","开盘","最高","最低","成交量","成交额"]:
                    if col in hist.columns: hist[col]=pd.to_numeric(hist[col],errors="coerce")
                hist["MA20"]=hist["收盘"].rolling(20).mean()
                hist["MA60"]=hist["收盘"].rolling(60).mean()
                st.line_chart(hist.set_index("日期")[["收盘","MA20","MA60"]].tail(250))
                st.dataframe(hist.tail(30),use_container_width=True,hide_index=True)
        except Exception as e:
            st.error("历史日线获取失败")
            st.code(f"{type(e).__name__}: {str(e)[:600]}")

st.divider()
st.caption("A股猎手 Quant 1.1｜第三方公开行情连接测试版，不构成投资建议。")
