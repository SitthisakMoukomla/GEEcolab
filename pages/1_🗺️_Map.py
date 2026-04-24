"""Map page — แผนที่ interactive"""
from __future__ import annotations

import ee
import geemap.foliumap as geemap
import pandas as pd
import plotly.express as px
import streamlit as st

from gee_utils.analysis import (
    burn_recurrence,
    dnbr_year,
    dynamic_world_year,
    get_aoi,
    get_province,
    lst_anomaly,
    lst_baseline,
)
from gee_utils.auth import initialize_gee
from gee_utils.constants import (
    DW_CLASS_NAMES,
    DW_PALETTE,
    PAL_ANOMALY,
    PAL_DNBR,
    PAL_LST,
    PAL_RECURRENCE,
    PROVINCE_EN,
    PROVINCE_TH,
    YEARS,
)
from gee_utils.landsat import lst_dry_season

st.set_page_config(page_title="🗺️ Map", page_icon="🗺️", layout="wide")
initialize_gee()


# ---- Cached computations ----
@st.cache_resource
def _get_aoi():
    return get_aoi()


@st.cache_resource
def _get_baseline():
    return lst_baseline(_get_aoi())


aoi = _get_aoi()
baseline = _get_baseline()


# ---- Sidebar controls ----
st.sidebar.header("🎛️ ตัวควบคุม")

province_th = st.sidebar.selectbox(
    "📍 จังหวัด",
    ["ทั้งภาคเหนือ"] + sorted(PROVINCE_EN.keys()),
    key="province_th",
)

layer_options = {
    "recurrence": "พื้นที่เผาซ้ำ (10 ปี)",
    "anomaly": "LST Anomaly (z-score)",
    "dnbr": "dNBR รายปี",
    "lst": "LST ฤดูแล้ง (°C)",
    "landcover": "Land cover (Dynamic World)",
}
layer = st.sidebar.radio(
    "🗺️ เลเยอร์",
    list(layer_options.keys()),
    format_func=lambda k: layer_options[k],
    key="layer",
)

year = st.sidebar.slider(
    "📅 ปี (สำหรับ anomaly / dNBR / LST / landcover)",
    min_value=YEARS[0],
    max_value=YEARS[-1],
    key="year",
)

st.sidebar.markdown("**🎚️ dNBR threshold**")
st.sidebar.caption("0.10 low · 0.27 moderate · 0.44 high")
threshold = st.sidebar.slider(
    "ค่า threshold", 0.10, 0.80, step=0.01, key="dnbr_threshold"
)

st.sidebar.markdown("**📆 ช่วงเดือนเปรียบเทียบ (dNBR)**")
pre_month = st.sidebar.slider("ก่อนไฟ (ปีก่อนหน้า)", 9, 12, key="pre_month")
post_month = st.sidebar.slider("หลังไฟ (ปีปัจจุบัน)", 4, 7, key="post_month")

opacity = st.sidebar.slider("🔳 ความโปร่งใส", 0.0, 1.0, step=0.05, key="opacity")
show_firms = st.sidebar.checkbox("🔥 แสดง FIRMS active fire", value=False)


# ---- AOI selection ----
if province_th != "ทั้งภาคเหนือ":
    display_aoi = get_province(PROVINCE_EN[province_th])
    zoom = 9
else:
    display_aoi = aoi
    zoom = 7


# ---- KPI row ----
st.title("🗺️ Interactive Map")
st.caption(f"จังหวัด: **{province_th}** · ปี: **{year}** · เลเยอร์: **{layer_options[layer]}**")

kpi_col1, kpi_col2, kpi_col3 = st.columns(3)


@st.cache_data(ttl=3600, show_spinner=False)
def _compute_kpis(year, pre_month, post_month, threshold, province_th):
    _aoi = (
        get_province(PROVINCE_EN[province_th])
        if province_th != "ทั้งภาคเหนือ"
        else get_aoi()
    )
    geom = _aoi.geometry()

    try:
        rec = burn_recurrence(pre_month, post_month, threshold, _aoi)
        recurrent_area = (
            rec.gte(3)
            .multiply(ee.Image.pixelArea())
            .divide(1e6)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geom,
                scale=120,
                maxPixels=1e13,
                bestEffort=True,
            )
            .get("recurrence")
            .getInfo()
        )
    except Exception:
        recurrent_area = None

    try:
        lst = lst_dry_season(year, _aoi)
        lst_mean = (
            lst.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=120,
                maxPixels=1e13,
                bestEffort=True,
            )
            .get("LST")
            .getInfo()
        )
    except Exception:
        lst_mean = None

    try:
        total_area = (
            ee.Image.pixelArea()
            .divide(1e6)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geom,
                scale=120,
                maxPixels=1e13,
                bestEffort=True,
            )
            .get("area")
            .getInfo()
        )
    except Exception:
        total_area = None

    return recurrent_area, lst_mean, total_area


with st.spinner("กำลังคำนวณสถิติ..."):
    recurrent_area, lst_mean, total_area = _compute_kpis(
        year, pre_month, post_month, threshold, province_th
    )

kpi_col1.metric(
    "พื้นที่เผาซ้ำ (≥3 ครั้ง)",
    f"{recurrent_area:,.0f} km²" if recurrent_area else "—",
)
kpi_col2.metric(
    "LST เฉลี่ยฤดูแล้ง",
    f"{lst_mean:.1f} °C" if lst_mean else "—",
)
if recurrent_area and total_area:
    kpi_col3.metric(
        "% พื้นที่เผาซ้ำ",
        f"{recurrent_area / total_area * 100:.1f} %",
    )
else:
    kpi_col3.metric("% พื้นที่เผาซ้ำ", "—")


# ---- Build map ----
m = geemap.Map(
    center=[18.7, 99.5], zoom=zoom, basemap="HYBRID",
    plugin_Draw=False, search_control=False, measure_control=False,
)

# Outline
outline = (
    ee.Image()
    .byte()
    .paint(featureCollection=aoi, color=1, width=2)
)
m.addLayer(outline, {"palette": ["#ffffff"]}, "ขอบเขตจังหวัด")

clipped_aoi = display_aoi

if layer == "recurrence":
    rec = burn_recurrence(pre_month, post_month, threshold, aoi).clip(clipped_aoi)
    masked = rec.updateMask(rec.gt(0))
    m.addLayer(
        masked,
        {"min": 1, "max": 10, "palette": PAL_RECURRENCE, "opacity": opacity},
        f"พื้นที่เผาซ้ำ (ครั้ง) threshold={threshold}",
    )
    vis = ("จำนวนครั้งที่เผา", 1, 10, PAL_RECURRENCE)

elif layer == "anomaly":
    sta = lst_anomaly(year, baseline, aoi).clip(clipped_aoi)
    m.addLayer(
        sta,
        {"min": -3, "max": 3, "palette": PAL_ANOMALY, "opacity": opacity},
        f"LST Anomaly z-score {year}",
    )
    vis = (f"LST Anomaly {year} (z-score)", -3, 3, PAL_ANOMALY)

elif layer == "dnbr":
    dnbr = dnbr_year(year, pre_month, post_month, aoi).clip(clipped_aoi)
    m.addLayer(
        dnbr,
        {"min": -0.2, "max": 0.8, "palette": PAL_DNBR, "opacity": opacity},
        f"dNBR {year}",
    )
    vis = (f"dNBR {year}", -0.2, 0.8, PAL_DNBR)

elif layer == "lst":
    lst = lst_dry_season(year, aoi).clip(clipped_aoi)
    m.addLayer(
        lst,
        {"min": 20, "max": 45, "palette": PAL_LST, "opacity": opacity},
        f"LST ฤดูแล้ง {year} (°C)",
    )
    vis = (f"LST ฤดูแล้ง {year} (°C)", 20, 45, PAL_LST)

else:  # landcover
    dw = dynamic_world_year(year, aoi).clip(clipped_aoi)
    m.addLayer(
        dw,
        {"min": 0, "max": 8, "palette": DW_PALETTE, "opacity": opacity},
        f"Dynamic World {year}",
    )
    vis = (f"Dynamic World {year}", 0, 8, DW_PALETTE)

if show_firms:
    firms = (
        ee.ImageCollection("FIRMS")
        .filterDate(
            ee.Date.fromYMD(year, 1, 1), ee.Date.fromYMD(year, 12, 31)
        )
        .select("T21")
        .max()
        .clip(clipped_aoi)
    )
    m.addLayer(
        firms,
        {"min": 325, "max": 400, "palette": ["red", "orange", "yellow"], "opacity": 0.8},
        f"FIRMS Active Fire {year}",
    )

m.centerObject(display_aoi, zoom)


# ---- Layout: map + legend/click info ----
map_col, info_col = st.columns([3, 1])

with map_col:
    m.to_streamlit(height=620)

with info_col:
    st.markdown(f"**Legend: {vis[0]}**")

    if layer == "landcover":
        for name, color in zip(DW_CLASS_NAMES, DW_PALETTE):
            from gee_utils.constants import DW_CLASS_TH

            st.markdown(
                f"<div style='display:flex;align-items:center;gap:6px;'>"
                f"<div style='width:18px;height:14px;background:{color};"
                f"border:1px solid #999;'></div>"
                f"{DW_CLASS_TH.get(name, name)}</div>",
                unsafe_allow_html=True,
            )
    else:
        _, vmin, vmax, palette = vis
        n = len(palette)
        steps = [vmin + (vmax - vmin) * i / (n - 1) for i in range(n)]
        for color, value in zip(palette, steps):
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:6px;'>"
                f"<div style='width:18px;height:14px;background:{color};"
                f"border:1px solid #999;'></div>{value:.2f}</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("**💡 Tips**")
    st.markdown(
        "- Zoom แผนที่ด้วย scroll / +-\n"
        "- เปลี่ยน layer ผ่าน radio ใน sidebar\n"
        "- ปรับ threshold / เดือน pre-post ดู scenarios\n"
        "- เปิด FIRMS เพื่อ validate burn scar"
    )


# ---- Time-series chart at AOI level ----
st.markdown("---")
st.subheader("📈 LST time-series — ค่าเฉลี่ยของพื้นที่ที่เลือก")


@st.cache_data(ttl=3600, show_spinner=False)
def _lst_ts(province_th):
    _aoi = (
        get_province(PROVINCE_EN[province_th])
        if province_th != "ทั้งภาคเหนือ"
        else get_aoi()
    )
    geom = _aoi.geometry()

    rows = []
    for y in YEARS:
        try:
            img = lst_dry_season(y, _aoi)
            mean = (
                img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geom,
                    scale=120,
                    maxPixels=1e13,
                    bestEffort=True,
                )
                .get("LST")
                .getInfo()
            )
        except Exception:
            mean = None
        rows.append({"year": y, "LST_°C": mean})
    return pd.DataFrame(rows)


with st.spinner("กำลังโหลด time-series..."):
    df_ts = _lst_ts(province_th)

if df_ts["LST_°C"].notna().any():
    fig = px.line(
        df_ts, x="year", y="LST_°C",
        markers=True,
        title=f"LST ฤดูแล้ง — {province_th}",
        labels={"year": "ปี", "LST_°C": "°C"},
    )
    fig.update_traces(line_color="#d73027")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("ไม่มีข้อมูลพอสำหรับ time-series")
