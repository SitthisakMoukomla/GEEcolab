# GEEcolab — วิเคราะห์พื้นที่เผาซ้ำซากภาคเหนือ

Google Earth Engine App แบบโต้ตอบได้ สำหรับวิเคราะห์ **พื้นที่เผาซ้ำซาก** และ **ความผิดปกติของอุณหภูมิผิวดิน (Surface Temperature Anomaly)** ในภาคเหนือของประเทศไทย ช่วงปี 2015–2024

## ฟีเจอร์

- **พื้นที่เผาซ้ำ (Burn Recurrence)** — นับจำนวนครั้งที่แต่ละ pixel ถูกเผาใน 10 ปี จาก dNBR
- **LST Anomaly (z-score)** — ดูความผิดปกติของอุณหภูมิผิวดินเทียบกับ baseline 10 ปี
- **dNBR รายปี** — ดูความรุนแรงของการเผาในปีที่เลือก
- **LST ฤดูแล้ง** — ดูอุณหภูมิผิวดินเฉลี่ยฤดูแล้ง
- **FIRMS Active Fire** — overlay จุด hotspot จาก VIIRS/MODIS (validation)
- **คลิกแผนที่** → กราฟ time-series LST ย้อนหลัง 10 ปีของ pixel นั้น
- **ปรับ dNBR threshold และช่วงเดือน pre/post** ผ่าน UI ได้

## ข้อมูลที่ใช้

| Dataset | การใช้งาน |
|---|---|
| `LANDSAT/LC08/C02/T1_L2` | Landsat 8 (SR + ST bands) |
| `LANDSAT/LC09/C02/T1_L2` | Landsat 9 (SR + ST bands) |
| `FIRMS` | Active fire hotspots (validation) |
| `FAO/GAUL/2015/level1` | ขอบเขตจังหวัด |

## พื้นที่ศึกษา

9 จังหวัดภาคเหนือ: เชียงใหม่, เชียงราย, แม่ฮ่องสอน, ลำปาง, ลำพูน, น่าน, พะเยา, แพร่, อุตรดิตถ์

## วิธีใช้

### 1. เปิด Google Earth Engine Code Editor

ไปที่ [code.earthengine.google.com](https://code.earthengine.google.com) (ต้องมี GEE account)

### 2. วางโค้ด

เปิด `src/app.js` คัดลอกทั้งหมดแล้วไปวางใน Code Editor

### 3. กด Run

รอประมาณ 30–60 วินาที โหลดเลเยอร์ครั้งแรก

### 4. ใช้งาน

- เลือก **จังหวัด** เพื่อ zoom
- เลื่อน **ปี** เพื่อดู anomaly/dNBR รายปี
- เลือก **เลเยอร์** ที่ต้องการ
- ปรับ **dNBR threshold** (0.27 = moderate, 0.44 = high)
- ปรับ **เดือน pre/post** สำหรับ dNBR (ค่าปริยาย: pre=พ.ย., post=พ.ค.)
- **คลิกบนแผนที่** → กราฟ LST 10 ปีของจุดนั้น

### 5. Publish เป็น App (ตัวเลือก)

ใน Code Editor → Apps → New → ตั้งชื่อ → Publish

## โครงสร้างโปรเจกต์

```
GEEcolab/
├── src/
│   └── app.js              # GEE App (copy-paste เข้า Code Editor)
├── docs/
│   └── methodology.md      # อธิบายสูตรและค่า threshold
└── README.md
```

## Insight ที่ได้จากการวิเคราะห์

จากข้อมูล 2015–2024 สามารถใช้ App ตอบคำถาม:

1. **พื้นที่ไหนถูกเผาซ้ำมากที่สุด** — hotspot ของ burn recurrence (≥3 ครั้ง) คือพื้นที่ที่ควรวาง fire break / lookout tower
2. **ปีไหนเผารุนแรงที่สุด** — เลื่อน year slider เทียบ dNBR รายปี
3. **LST anomaly สัมพันธ์กับ burn recurrence ไหม** — เลเยอร์ STA ช่วยเห็นพื้นที่ร้อนผิดปกติที่อาจเสี่ยงเผา
4. **ขอบเขตเขต burned ที่ FIRMS จับไม่ได้** — FIRMS เห็นเฉพาะตอนไฟกำลังลุก dNBR เห็น scar หลังไฟดับแล้ว

## ข้อจำกัด

- Landsat revisit 16 วัน — บางเดือนอาจมีเมฆบังจนไม่มีข้อมูล
- dNBR threshold ควร calibrate ตาม ecosystem (ป่าเต็งรัง vs ป่าดิบ vs เกษตร)
- GEE App มี compute quota — การคำนวณ recurrence 10 ปีอาจช้าในโหลดแรก
- ฤดูแล้งในแต่ละปีไม่ตรงกัน อาจต้องปรับเดือน pre/post

## อ่านเพิ่ม

ดูรายละเอียดสูตรและค่าอ้างอิงที่ [`docs/methodology.md`](docs/methodology.md)

## License

MIT
