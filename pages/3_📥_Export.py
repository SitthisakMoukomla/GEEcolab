"""Export page — ส่งออก GeoTIFF ไป Drive / download CSV"""
from __future__ import annotations

import datetime as dt

import ee
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
from gee_utils.constants import PROVINCE_EN, YEARS
from gee_utils.landsat import lst_dry_season

st.set_page_config(page_title="📥 Export", page_icon="📥", layout="wide")
initialize_gee()

st.title("📥 Export — ส่งออก GeoTIFF")
st.markdown(
    "ส่งออกเลเยอร์ที่คำนวณไป **Google Drive** ของคุณ "
    "(ต้อง auth ด้วย Google account เดียวกับที่เชื่อม GEE)"
)

st.warning(
    "🔸 งาน export จะถูก submit เป็น **Task** บน GEE — "
    "ตรวจสถานะที่ [Earth Engine Tasks page](https://code.earthengine.google.com/tasks) "
    "ไฟล์จะปรากฏใน Google Drive folder `GEE_exports` หลัง task เสร็จ (5–30 นาที)"
)


# ---- Cached resources ----
@st.cache_resource
def _aoi():
    return get_aoi()


@st.cache_resource
def _baseline():
    return lst_baseline(_aoi())


aoi = _aoi()


# ---- Form ----
st.subheader("⚙️ ตั้งค่า Export")

with st.form("export_form"):
    col1, col2 = st.columns(2)
    with col1:
        layer = st.selectbox(
            "เลเยอร์ที่ต้องการ export",
            [
                "recurrence — พื้นที่เผาซ้ำ 10 ปี",
                "dnbr — dNBR รายปี",
                "anomaly — LST Anomaly รายปี",
                "lst — LST ฤดูแล้งรายปี",
                "landcover — Dynamic World รายปี",
            ],
        )
        province = st.selectbox(
            "พื้นที่",
            ["ทั้งภาคเหนือ"] + sorted(PROVINCE_EN.keys()),
        )

    with col2:
        year = st.slider(
            "ปี (ใช้กับทุก layer ยกเว้น recurrence)",
            YEARS[0], YEARS[-1], YEARS[-1],
        )
        scale = st.select_slider(
            "Resolution (ม./pixel)", options=[30, 90, 120, 300, 500], value=90,
        )
        threshold = st.slider("dNBR threshold", 0.10, 0.80, value=0.27, step=0.01)
        pre_m = st.slider("เดือน pre", 9, 12, 11)
        post_m = st.slider("เดือน post", 4, 7, 5)

    submitted = st.form_submit_button("🚀 ส่งออก → Google Drive")


def _build_image(layer_key: str):
    export_aoi = (
        get_province(PROVINCE_EN[province]) if province != "ทั้งภาคเหนือ" else aoi
    )

    if layer_key == "recurrence":
        img = burn_recurrence(pre_m, post_m, threshold, aoi).clip(export_aoi)
        name = f"burn_recurrence_2015_2024_thr{threshold:.2f}"
    elif layer_key == "dnbr":
        img = dnbr_year(year, pre_m, post_m, aoi).clip(export_aoi)
        name = f"dnbr_{year}"
    elif layer_key == "anomaly":
        baseline = _baseline()
        img = lst_anomaly(year, baseline, aoi).clip(export_aoi)
        name = f"lst_anomaly_{year}"
    elif layer_key == "lst":
        img = lst_dry_season(year, aoi).clip(export_aoi)
        name = f"lst_dryseason_{year}"
    else:  # landcover
        img = dynamic_world_year(year, aoi).clip(export_aoi)
        name = f"dynamicworld_{year}"

    ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M")
    prov_slug = (
        PROVINCE_EN[province].lower().replace(" ", "_") if province != "ทั้งภาคเหนือ" else "north_th"
    )
    return img, f"{name}_{prov_slug}_{ts}", export_aoi


if submitted:
    try:
        layer_key = layer.split(" — ")[0]
        image, filename, export_aoi = _build_image(layer_key)

        task = ee.batch.Export.image.toDrive(
            image=image,
            description=filename,
            folder="GEE_exports",
            fileNamePrefix=filename,
            region=export_aoi.geometry(),
            scale=scale,
            maxPixels=int(1e13),
            fileFormat="GeoTIFF",
        )
        task.start()

        st.success(
            f"✅ Submit task แล้ว: `{filename}` · Task id: `{task.id}`\n\n"
            "เปิด [Earth Engine Tasks](https://code.earthengine.google.com/tasks) "
            "เพื่อดูสถานะ — ไฟล์จะเข้า Google Drive folder `GEE_exports`"
        )
    except Exception as exc:
        st.error(f"❌ Export ล้มเหลว: {exc}")


# ---- Thumbnail download (small preview) ----
st.markdown("---")
st.subheader("🖼️ Download PNG preview (ใช้กับพื้นที่เล็ก)")
st.caption(
    "วิธีนี้ทำงานแบบ synchronous — เหมาะกับพื้นที่จังหวัดเดียวและ resolution ต่ำ "
    "ถ้าพื้นที่ใหญ่ใช้ Export GeoTIFF ไป Drive แทน"
)

with st.form("thumb_form"):
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        t_layer = st.selectbox(
            "Layer",
            ["recurrence", "dnbr", "anomaly", "lst", "landcover"],
            key="thumb_layer",
        )
        t_prov = st.selectbox(
            "จังหวัด (ต้องเลือก ไม่ใช่ทั้งภาค)",
            sorted(PROVINCE_EN.keys()),
            key="thumb_prov",
        )
    with t_col2:
        t_year = st.slider("ปี", YEARS[0], YEARS[-1], YEARS[-1], key="thumb_year")
        t_dim = st.select_slider(
            "ขนาดภาพ (px)",
            options=[256, 512, 768, 1024, 1280],
            value=768,
        )

    thumb_submit = st.form_submit_button("สร้าง PNG preview")


if thumb_submit:
    try:
        thumb_aoi = get_province(PROVINCE_EN[t_prov])
        from gee_utils.constants import (
            PAL_ANOMALY, PAL_DNBR, PAL_LST, PAL_RECURRENCE, DW_PALETTE,
        )

        if t_layer == "recurrence":
            img = burn_recurrence(pre_m, post_m, threshold, aoi).clip(thumb_aoi)
            vis = {"min": 1, "max": 10, "palette": PAL_RECURRENCE}
        elif t_layer == "dnbr":
            img = dnbr_year(t_year, pre_m, post_m, aoi).clip(thumb_aoi)
            vis = {"min": -0.2, "max": 0.8, "palette": PAL_DNBR}
        elif t_layer == "anomaly":
            img = lst_anomaly(t_year, _baseline(), aoi).clip(thumb_aoi)
            vis = {"min": -3, "max": 3, "palette": PAL_ANOMALY}
        elif t_layer == "lst":
            img = lst_dry_season(t_year, aoi).clip(thumb_aoi)
            vis = {"min": 20, "max": 45, "palette": PAL_LST}
        else:
            img = dynamic_world_year(t_year, aoi).clip(thumb_aoi)
            vis = {"min": 0, "max": 8, "palette": DW_PALETTE}

        url = img.getThumbURL(
            {
                **vis,
                "region": thumb_aoi.geometry(),
                "dimensions": t_dim,
                "format": "png",
            }
        )

        import urllib.request

        with urllib.request.urlopen(url) as resp:
            png_bytes = resp.read()

        st.image(png_bytes, caption=f"{t_layer} · {t_prov} · {t_year}")
        st.download_button(
            "💾 Download PNG",
            png_bytes,
            file_name=f"{t_layer}_{t_prov}_{t_year}.png",
            mime="image/png",
        )
    except Exception as exc:
        st.error(f"❌ สร้าง preview ไม่สำเร็จ: {exc}")
