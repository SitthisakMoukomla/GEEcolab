# GEEcolab — วิเคราะห์พื้นที่เผาซ้ำซากภาคเหนือ

Dashboard วิเคราะห์ **พื้นที่เผาซ้ำซาก** และ **Surface Temperature Anomaly** ในภาคเหนือของประเทศไทย (2015–2024) ด้วย Landsat 8/9 + dNBR + Dynamic World

## โปรเจกต์มี 2 เวอร์ชัน

| เวอร์ชัน | ไฟล์ | ใช้เมื่อไหร่ |
|---|---|---|
| **GEE App (JavaScript)** | `src/app.js` | อยากได้ web app เร็ว ๆ ไม่ setup server เอง — paste ใน Code Editor แล้ว publish |
| **Streamlit Dashboard (Python)** | `streamlit_app.py` + `pages/` | อยากได้ dashboard ซับซ้อน (charts, tables, downloads, multi-page) |

ทั้งสองเวอร์ชันใช้สูตรเดียวกัน — ดูรายละเอียดที่ [`docs/methodology.md`](docs/methodology.md)

---

## 🐍 Streamlit Dashboard

### ฟีเจอร์

**3 หน้า:**

1. **🗺️ Map** — แผนที่ interactive, สลับ layer (recurrence/anomaly/dNBR/LST/landcover), KPI cards, time-series chart
2. **📊 Analytics** — bar chart burn area รายปี, LST anomaly trend, recurrence histogram, top จังหวัด, land cover breakdown
3. **📥 Export** — ส่งออก GeoTIFF ไป Google Drive, download CSV stats, PNG preview

### รัน Local

```bash
# 1. Clone และ install
git clone <repo> && cd GEEcolab
pip install -r requirements.txt

# 2. Auth GEE (ครั้งแรกเท่านั้น)
earthengine authenticate

# 3. รัน
streamlit run streamlit_app.py
```

เปิด [http://localhost:8501](http://localhost:8501) บน browser

### Deploy บน Streamlit Community Cloud

**ข้อกำหนด:**
- GCP project ที่เปิด Earth Engine API
- Service account ที่ได้สิทธิ์ `Earth Engine Resource Viewer`
- ไฟล์ JSON key ของ service account

**ขั้นตอน:**

1. Push repo ไป GitHub
2. ไปที่ [share.streamlit.io](https://share.streamlit.io) → **New app**
3. เลือก repo + branch + main file = `streamlit_app.py`
4. ไป **Settings → Secrets** ใส่:

```toml
GEE_PROJECT_ID = "your-gcp-project-id"
GEE_SERVICE_ACCOUNT_JSON = """
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "your-sa@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
"""
```

5. Deploy

**สำคัญ:** Service account ต้อง register กับ Earth Engine ที่ [code.earthengine.google.com/register](https://code.earthengine.google.com/register)

### โครงสร้างโค้ด

```
GEEcolab/
├── streamlit_app.py              # Entry page
├── pages/
│   ├── 1_🗺️_Map.py                # Interactive map
│   ├── 2_📊_Analytics.py          # Charts + tables
│   └── 3_📥_Export.py             # Download GeoTIFF/CSV/PNG
├── gee_utils/
│   ├── __init__.py
│   ├── auth.py                    # GEE init (service account + user)
│   ├── constants.py               # provinces, palettes, Dynamic World classes
│   ├── landsat.py                 # cloud mask, scale, LST, NBR
│   └── analysis.py                # dNBR, recurrence, anomaly, stats
├── .streamlit/config.toml         # theme
├── requirements.txt
├── src/app.js                     # GEE App (JavaScript) — เวอร์ชันเก่า
├── docs/methodology.md
└── README.md
```

---

## 🌐 GEE App (JavaScript)

ถ้าแค่อยากได้ web app พร้อมใช้โดยไม่ต้อง setup Python:

1. เปิด [code.earthengine.google.com](https://code.earthengine.google.com)
2. Copy ทั้งไฟล์ `src/app.js` ไปวาง
3. กด Run
4. Apps → New → Publish → ได้ URL

รายละเอียดเพิ่ม: ดูคอมเมนต์ด้านบน `src/app.js`

---

## ข้อมูลที่ใช้

| Dataset | หน้าที่ |
|---|---|
| `LANDSAT/LC08/C02/T1_L2` | Landsat 8 SR + ST (2013–ปัจจุบัน) |
| `LANDSAT/LC09/C02/T1_L2` | Landsat 9 SR + ST (2021–ปัจจุบัน) |
| `GOOGLE/DYNAMICWORLD/V1` | Land Cover 10 m (2015–ปัจจุบัน) |
| `FAO/GAUL/2015/level1` | ขอบเขตจังหวัด |
| `FIRMS` | Active fire hotspots |

## พื้นที่ศึกษา

9 จังหวัดภาคเหนือ: เชียงใหม่, เชียงราย, แม่ฮ่องสอน, ลำปาง, ลำพูน, น่าน, พะเยา, แพร่, อุตรดิตถ์

## Insight ที่ได้

- **พื้นที่ที่ต้องวาง fire break** — burn recurrence ≥3 ครั้ง (จาก Analytics → Top จังหวัด)
- **Land cover ของ recurrent burn** — ดูว่าเป็นป่า/เกษตร/ไม้พุ่ม (Analytics → land cover pie)
- **Trend อุณหภูมิ** — LST anomaly ขึ้น/ลง ในแต่ละปี (Analytics → line chart)
- **Validation** — เปรียบเทียบ dNBR กับ FIRMS hotspots (Map → toggle FIRMS)

## ข้อจำกัด

- Landsat revisit 16 วัน — เมฆในไทยเยอะ บางปี pre/post window อาจไม่มีข้อมูล
- dNBR threshold ควร calibrate ตาม ecosystem (ป่าเต็งรัง/ป่าดิบ/เกษตร)
- GEE compute quota — Dashboard หน้าแรกอาจใช้ 1–2 นาทีโหลด
- Baseline 10 ปีสั้น — climatology ทั่วไปใช้ 30 ปี

## References

ดู [`docs/methodology.md`](docs/methodology.md)

## License

MIT
