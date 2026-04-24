# วิธี Deploy Streamlit Dashboard

คู่มือ end-to-end สำหรับ deploy `streamlit_app.py` ขึ้น **Streamlit Community Cloud**

## ขั้นที่ 1 — เปิด Earth Engine API บน GCP

1. ไป [console.cloud.google.com](https://console.cloud.google.com)
2. สร้าง **new project** (หรือใช้ project เดิม) จด `PROJECT_ID` ไว้
3. ไปที่ **APIs & Services → Library** → ค้น "Earth Engine API" → **Enable**

## ขั้นที่ 2 — สร้าง Service Account

1. [console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. **Create service account**
   - ชื่อ: `streamlit-gee`
   - Role: **Earth Engine Resource Viewer** (หรือ Owner เพื่อความสะดวก)
3. หลังสร้างเสร็จ → เปิด service account → tab **Keys**
4. **Add Key → Create new key → JSON** → ดาวน์โหลดไฟล์ (ห้ามทำหาย!)

## ขั้นที่ 3 — Register Service Account กับ Earth Engine

1. ไป [code.earthengine.google.com/register](https://code.earthengine.google.com/register)
2. เลือก **Register a Service Account for use with a Cloud Project**
3. ใส่ email ของ service account (`streamlit-gee@PROJECT.iam.gserviceaccount.com`)
4. เลือก project ที่เปิด EE API
5. Submit

## ขั้นที่ 4 — Deploy บน Streamlit Cloud

1. ไป [share.streamlit.io](https://share.streamlit.io) login ด้วย GitHub
2. **New app** → เลือก:
   - Repository: `SitthisakMoukomla/GEEcolab`
   - Branch: `main`
   - Main file: `streamlit_app.py`
3. **Advanced settings → Secrets** — paste:

```toml
GEE_PROJECT_ID = "your-gcp-project-id"

GEE_SERVICE_ACCOUNT_JSON = """
<วาง JSON key ทั้งก้อนที่ดาวน์โหลดจากขั้นที่ 2>
"""
```

4. **Deploy** — รอ ~2 นาที แรกจะ pip install ช้าหน่อย

## ขั้นที่ 5 — ทดสอบ

- เปิด URL ที่ Streamlit Cloud ให้มา
- ควรเห็นหน้า Landing ขึ้นทันทีถ้า auth สำเร็จ
- ไป `🗺️ Map` page → เลือกจังหวัด → รอ map render (30–60 วิ. ครั้งแรก)

## Troubleshooting

| Error | แก้ยังไง |
|---|---|
| `EEException: Not signed up for Earth Engine` | ยังไม่ได้ register service account ที่ขั้น 3 |
| `google.auth.exceptions.RefreshError` | JSON key ไม่ครบ หรือ escape `\\n` ใน private_key หาย |
| `Permission denied: earthengine.computations.create` | Role ใน IAM ไม่พอ — เปลี่ยนเป็น Owner หรือเพิ่ม `Earth Engine Resource Writer` |
| Map ไม่ขึ้น ค้างนาน | ครั้งแรกจะช้าเพราะ compute LST baseline 10 ปี — รอได้ |

## รันใน Local (ทดสอบก่อน Deploy)

```bash
pip install -r requirements.txt
earthengine authenticate            # ครั้งแรก
streamlit run streamlit_app.py
```

เปิด [http://localhost:8501](http://localhost:8501)
