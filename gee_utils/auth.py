"""จัดการ Google Earth Engine authentication

รองรับ 2 โหมด:
1. Service Account (สำหรับ deploy บน Streamlit Cloud / Cloud Run)
   ตั้งค่าผ่าน st.secrets["GEE_SERVICE_ACCOUNT_JSON"] (stringified JSON)
   และ st.secrets["GEE_PROJECT_ID"] (optional)
2. User credentials (สำหรับ local dev)
   ต้องรัน `earthengine authenticate` ก่อนครั้งแรก
"""
from __future__ import annotations

import json
import os

import ee
import streamlit as st


@st.cache_resource
def initialize_gee() -> bool:
    """Init GEE — cached เพื่อไม่ให้ init ซ้ำทุก rerun"""
    try:
        if "GEE_SERVICE_ACCOUNT_JSON" in st.secrets:
            sa_json = st.secrets["GEE_SERVICE_ACCOUNT_JSON"]
            sa_info = json.loads(sa_json) if isinstance(sa_json, str) else dict(sa_json)
            creds = ee.ServiceAccountCredentials(
                email=sa_info["client_email"],
                key_data=json.dumps(sa_info),
            )
            project = st.secrets.get("GEE_PROJECT_ID", sa_info.get("project_id"))
            ee.Initialize(creds, project=project)
            return True

        project = os.environ.get("GEE_PROJECT_ID") or st.secrets.get("GEE_PROJECT_ID", None)
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
        return True
    except Exception as exc:
        st.error(
            "❌ เชื่อมต่อ Google Earth Engine ไม่สำเร็จ\n\n"
            f"Error: {exc}\n\n"
            "**วิธีแก้:**\n"
            "- **Local:** รัน `earthengine authenticate` ใน terminal\n"
            "- **Streamlit Cloud:** ตั้ง `GEE_SERVICE_ACCOUNT_JSON` และ "
            "`GEE_PROJECT_ID` ใน Secrets"
        )
        st.stop()
        return False
