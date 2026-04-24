"""Streamlit Dashboard — วิเคราะห์พื้นที่เผาซ้ำซากภาคเหนือ (2015–2024)

Entry page + ตั้งค่าแอปทั้งหมด + init GEE
รัน: `streamlit run streamlit_app.py`
"""
from __future__ import annotations

import streamlit as st

from gee_utils.auth import initialize_gee
from gee_utils.constants import NORTHERN_PROVINCES, YEARS

st.set_page_config(
    page_title="Fire Recurrence Dashboard — ภาคเหนือ",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_gee()

# ---- Session state defaults ----
defaults = {
    "province_th": "ทั้งภาคเหนือ",
    "year": 2024,
    "layer": "recurrence",
    "dnbr_threshold": 0.27,
    "pre_month": 11,
    "post_month": 5,
    "opacity": 0.75,
    "last_click": None,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


# ---- Landing ----
st.title("🔥 วิเคราะห์พื้นที่เผาซ้ำซาก — ภาคเหนือของประเทศไทย")
st.markdown(
    "Dashboard สำหรับวิเคราะห์**พื้นที่เผาซ้ำซาก**และ**ความผิดปกติของอุณหภูมิผิวดิน**"
    " (Surface Temperature Anomaly) ในภาคเหนือช่วงปี 2015–2024 "
    "เพื่อช่วยสนับสนุนการจัดการไฟป่า"
)

st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("พื้นที่ศึกษา", f"{len(NORTHERN_PROVINCES)} จังหวัด")
with col2:
    st.metric("ช่วงเวลา", f"{YEARS[0]}–{YEARS[-1]} ({len(YEARS)} ปี)")
with col3:
    st.metric("Satellite", "Landsat 8 + 9")

st.markdown("---")

st.subheader("📋 หน้าต่างต่าง ๆ ของ Dashboard")

pages = [
    (
        "🗺️ Map",
        "แผนที่ interactive — เลือก layer (recurrence / anomaly / dNBR / LST), "
        "ปรับ threshold และช่วงเดือน pre/post, คลิก pixel ดูกราฟ LST 10 ปี",
    ),
    (
        "📊 Analytics",
        "กราฟและตาราง — burn area รายปี, LST anomaly trend, "
        "top จังหวัด, land cover ของ recurrent burn (Dynamic World)",
    ),
    (
        "📥 Export",
        "ส่งออก GeoTIFF ไป Google Drive, download CSV สถิติ, "
        "capture PNG ของแผนที่",
    ),
]
for title, desc in pages:
    st.markdown(f"**{title}**  \n{desc}")

st.markdown("---")

with st.expander("ℹ️ ข้อมูลที่ใช้และสมมติฐาน"):
    st.markdown(
        """
        | Dataset | หน้าที่ |
        |---|---|
        | `LANDSAT/LC08/C02/T1_L2` | Landsat 8 SR + ST bands |
        | `LANDSAT/LC09/C02/T1_L2` | Landsat 9 SR + ST bands |
        | `GOOGLE/DYNAMICWORLD/V1` | Land cover 10 m (Dynamic World) |
        | `FAO/GAUL/2015/level1` | ขอบเขตจังหวัด |
        | `FIRMS` | Active fire hotspots (validation) |

        **Cloud mask:** `QA_PIXEL` bits 1/3/4/5 + `QA_RADSAT == 0`
        **ฤดูแล้ง:** ธ.ค. (ปีก่อน) – เม.ย. (ปีปัจจุบัน)
        **Baseline:** ค่าเฉลี่ย/ส่วนเบี่ยงเบน LST ฤดูแล้งตลอด 10 ปี
        **dNBR:** NBR_pre − NBR_post (ปรับเดือนและ threshold ได้ผ่าน sidebar)

        ดูรายละเอียดสูตร references ที่ [`docs/methodology.md`](docs/methodology.md)
        """
    )

with st.expander("🚀 วิธี deploy บน Streamlit Community Cloud"):
    st.markdown(
        """
        1. Push repo นี้ไป GitHub
        2. ไปที่ [share.streamlit.io](https://share.streamlit.io) → New app
        3. เลือก repo + branch + main file = `streamlit_app.py`
        4. ใส่ Secrets (Settings → Secrets):
           ```toml
           GEE_PROJECT_ID = "your-gcp-project"
           GEE_SERVICE_ACCOUNT_JSON = '''
           {
             "type": "service_account",
             "project_id": "...",
             "private_key": "...",
             "client_email": "...@....iam.gserviceaccount.com",
             ...
           }
           '''
           ```
        5. Deploy

        **Service account ต้องได้สิทธิ์ Earth Engine Resource Viewer**
        ใน [GEE admin](https://code.earthengine.google.com/register)
        """
    )

st.caption("🌿 Landsat Thermal + dNBR · Built with Streamlit + geemap")
