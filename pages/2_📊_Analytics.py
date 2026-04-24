"""Analytics page — charts + tables"""
from __future__ import annotations

import ee
import pandas as pd
import plotly.express as px
import streamlit as st

from gee_utils.analysis import (
    burned_area_per_year,
    get_aoi,
    landcover_of_recurrent_burn,
    lst_anomaly_mean_per_year,
    recurrence_by_province,
    recurrence_histogram,
)
from gee_utils.auth import initialize_gee
from gee_utils.constants import (
    DW_CLASS_NAMES,
    DW_CLASS_TH,
    DW_PALETTE,
    PROVINCE_TH,
    YEARS,
)

st.set_page_config(page_title="📊 Analytics", page_icon="📊", layout="wide")
initialize_gee()

st.title("📊 Analytics")

# ---- Shared controls ----
with st.sidebar:
    st.header("🎛️ พารามิเตอร์")
    threshold = st.slider("dNBR threshold", 0.10, 0.80, step=0.01, key="dnbr_threshold")
    pre_month = st.slider("เดือน pre", 9, 12, key="pre_month")
    post_month = st.slider("เดือน post", 4, 7, key="post_month")
    lc_year = st.slider("ปีของ Dynamic World", YEARS[0], YEARS[-1], key="year")

st.caption(
    f"threshold=**{threshold}** · pre=**{pre_month}** · post=**{post_month}** "
    f"· land cover year=**{lc_year}**"
)


# ---- Data loaders ----
@st.cache_data(ttl=3600, show_spinner="กำลังคำนวณพื้นที่เผารายปี...")
def _burned_per_year(pre_m, post_m, thr):
    aoi = get_aoi()
    fc = burned_area_per_year(pre_m, post_m, thr, aoi)
    data = fc.getInfo()
    rows = [
        {"year": f["properties"]["year"], "area_km2": f["properties"]["area_km2"]}
        for f in data["features"]
    ]
    return pd.DataFrame(rows).dropna()


@st.cache_data(ttl=3600, show_spinner="กำลังคำนวณ LST anomaly trend...")
def _sta_per_year():
    aoi = get_aoi()
    fc = lst_anomaly_mean_per_year(aoi)
    data = fc.getInfo()
    rows = [
        {"year": f["properties"]["year"], "sta_mean": f["properties"]["sta_mean"]}
        for f in data["features"]
    ]
    return pd.DataFrame(rows).dropna()


@st.cache_data(ttl=3600, show_spinner="กำลังสร้าง recurrence histogram...")
def _hist(pre_m, post_m, thr):
    aoi = get_aoi()
    hist = recurrence_histogram(pre_m, post_m, thr, aoi).getInfo()
    if not hist:
        return pd.DataFrame(columns=["recurrence", "pixels"])
    rows = [
        {"recurrence": int(float(k)), "pixels": int(v)}
        for k, v in hist.items()
    ]
    df = pd.DataFrame(rows).sort_values("recurrence")
    df["area_km2"] = df["pixels"] * 90 * 90 / 1e6
    return df


@st.cache_data(ttl=3600, show_spinner="กำลังจัดอันดับจังหวัด...")
def _province_rank(pre_m, post_m, thr):
    fc = recurrence_by_province(pre_m, post_m, thr)
    data = fc.getInfo()
    rows = []
    for f in data["features"]:
        p = f["properties"]
        rows.append(
            {
                "จังหวัด": PROVINCE_TH.get(p.get("ADM1_NAME"), p.get("ADM1_NAME")),
                "พื้นที่เผาซ้ำ ≥3 ครั้ง (km²)": p.get("recurrent_km2"),
            }
        )
    return pd.DataFrame(rows).dropna()


@st.cache_data(ttl=3600, show_spinner="กำลังวิเคราะห์ land cover...")
def _lc_of_recurrent(pre_m, post_m, thr, year):
    aoi = get_aoi()
    hist = landcover_of_recurrent_burn(pre_m, post_m, thr, year, aoi).getInfo()
    if not hist:
        return pd.DataFrame(columns=["class", "pixels"])
    rows = []
    for k, v in hist.items():
        idx = int(float(k))
        if 0 <= idx < len(DW_CLASS_NAMES):
            cls_en = DW_CLASS_NAMES[idx]
            rows.append(
                {
                    "class": DW_CLASS_TH[cls_en],
                    "class_en": cls_en,
                    "pixels": int(v),
                    "area_km2": int(v) * 10 * 10 / 1e6,
                    "color": DW_PALETTE[idx],
                }
            )
    return pd.DataFrame(rows).sort_values("pixels", ascending=False)


# ---- Row 1: burn area & STA ----
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 พื้นที่เผารายปี (km²)")
    df_burn = _burned_per_year(pre_month, post_month, threshold)
    if not df_burn.empty:
        fig = px.bar(
            df_burn, x="year", y="area_km2",
            labels={"year": "ปี", "area_km2": "พื้นที่เผา (km²)"},
            color="area_km2",
            color_continuous_scale="YlOrRd",
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"รวม 10 ปี: **{df_burn['area_km2'].sum():,.0f} km²** · "
            f"เฉลี่ย **{df_burn['area_km2'].mean():,.0f} km²/ปี**"
        )
    else:
        st.info("ไม่มีข้อมูล")

with col2:
    st.subheader("🌡️ LST Anomaly trend (ค่าเฉลี่ยทั้งภาค)")
    df_sta = _sta_per_year()
    if not df_sta.empty:
        fig = px.line(
            df_sta, x="year", y="sta_mean", markers=True,
            labels={"year": "ปี", "sta_mean": "z-score"},
        )
        fig.update_traces(line_color="#d73027")
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
        latest = df_sta.iloc[-1]
        st.caption(
            f"ล่าสุด ({int(latest['year'])}): **{latest['sta_mean']:+.2f}**"
            " (บวก = ร้อนกว่าปกติ)"
        )
    else:
        st.info("ไม่มีข้อมูล")


# ---- Row 2: histogram + province rank ----
col3, col4 = st.columns(2)

with col3:
    st.subheader("📊 Histogram จำนวนปีที่เผา")
    df_hist = _hist(pre_month, post_month, threshold)
    if not df_hist.empty:
        # ตัด 0 ออกเพื่อดู distribution ของที่เผาจริง
        df_plot = df_hist[df_hist["recurrence"] > 0]
        fig = px.bar(
            df_plot, x="recurrence", y="area_km2",
            labels={"recurrence": "จำนวนครั้งที่เผา", "area_km2": "พื้นที่ (km²)"},
            color="recurrence",
            color_continuous_scale="YlOrRd",
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

        recurrent = df_plot[df_plot["recurrence"] >= 3]["area_km2"].sum()
        st.caption(
            f"พื้นที่เผาซ้ำ ≥3 ครั้ง: **{recurrent:,.0f} km²**"
        )
    else:
        st.info("ไม่มีข้อมูล")

with col4:
    st.subheader("🏆 Top จังหวัด: พื้นที่เผาซ้ำ ≥3 ครั้ง")
    df_prov = _province_rank(pre_month, post_month, threshold)
    if not df_prov.empty:
        df_prov["พื้นที่เผาซ้ำ ≥3 ครั้ง (km²)"] = df_prov[
            "พื้นที่เผาซ้ำ ≥3 ครั้ง (km²)"
        ].round(1)
        st.dataframe(
            df_prov,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("ไม่มีข้อมูล")


# ---- Row 3: land cover breakdown ----
st.markdown("---")
st.subheader(f"🌳 Land cover ของพื้นที่เผาซ้ำ (Dynamic World {lc_year})")

df_lc = _lc_of_recurrent(pre_month, post_month, threshold, lc_year)
if not df_lc.empty:
    lc_col1, lc_col2 = st.columns([2, 3])

    with lc_col1:
        fig = px.pie(
            df_lc, names="class", values="area_km2",
            color="class",
            color_discrete_map=dict(zip(df_lc["class"], df_lc["color"])),
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with lc_col2:
        st.dataframe(
            df_lc[["class", "area_km2"]]
            .rename(
                columns={
                    "class": "ประเภท Land Cover",
                    "area_km2": "พื้นที่ (km²)",
                }
            )
            .round(1),
            use_container_width=True,
            hide_index=True,
        )

        top_class = df_lc.iloc[0]
        st.info(
            f"**Insight:** ประเภท Land Cover หลักของพื้นที่เผาซ้ำคือ "
            f"**{top_class['class']}** ({top_class['area_km2']:,.0f} km²)"
        )
else:
    st.info("ยังไม่มีข้อมูล")


# ---- Download CSV ----
st.markdown("---")
st.subheader("📥 Download ข้อมูลทั้งหมดเป็น CSV")

dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)
if not df_burn.empty:
    dl_col1.download_button(
        "Burned area/year", df_burn.to_csv(index=False),
        file_name="burned_area_per_year.csv",
        mime="text/csv",
    )
if not df_sta.empty:
    dl_col2.download_button(
        "STA trend", df_sta.to_csv(index=False),
        file_name="sta_trend.csv",
        mime="text/csv",
    )
if not df_prov.empty:
    dl_col3.download_button(
        "Province rank", df_prov.to_csv(index=False),
        file_name="recurrence_by_province.csv",
        mime="text/csv",
    )
if not df_lc.empty:
    dl_col4.download_button(
        "Land cover", df_lc[["class", "class_en", "area_km2"]].to_csv(index=False),
        file_name="landcover_of_recurrent_burn.csv",
        mime="text/csv",
    )
