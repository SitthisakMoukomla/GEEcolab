# Methodology — วิเคราะห์พื้นที่เผาซ้ำและ LST Anomaly

เอกสารนี้อธิบายสูตร ค่า threshold และสมมติฐานที่ใช้ใน `src/app.js`

## 1. Data Sources

### Landsat 8/9 Collection 2 Level 2

- `LANDSAT/LC08/C02/T1_L2` (2013–ปัจจุบัน)
- `LANDSAT/LC09/C02/T1_L2` (2021–ปัจจุบัน)

Bands ที่ใช้:

| Band | Wavelength | ใช้ทำอะไร |
|---|---|---|
| SR_B5 | NIR (0.85–0.88 µm) | NBR |
| SR_B7 | SWIR2 (2.11–2.29 µm) | NBR |
| ST_B10 | TIRS1 (10.60–11.19 µm) | LST |
| QA_PIXEL | QA bitmask | cloud/shadow mask |
| QA_RADSAT | Saturation mask | saturation mask |

### Scale factors (Collection 2 Level 2)

**Surface Reflectance:**
```
SR_actual = SR_raw * 0.0000275 − 0.2
```

**Surface Temperature (ST_B10 → Kelvin → Celsius):**
```
LST_Kelvin = ST_raw * 0.00341802 + 149.0
LST_Celsius = LST_Kelvin − 273.15
```

ที่มา: [USGS Landsat C2 L2 Science Product Guide](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products)

## 2. Cloud Masking

ใช้ bit mask จาก `QA_PIXEL`:

| Bit | ความหมาย |
|---|---|
| 1 | Dilated cloud |
| 3 | Cloud |
| 4 | Cloud shadow |
| 5 | Snow |

Pixel ที่ bit ใด bit หนึ่งตั้ง = 1 จะถูก mask ออก
เพิ่มเติมใช้ `QA_RADSAT == 0` กรอง saturated pixels

## 3. NBR (Normalized Burn Ratio)

```
NBR = (NIR − SWIR2) / (NIR + SWIR2)
    = (SR_B5 − SR_B7) / (SR_B5 + SR_B7)
```

- ค่าสูง (ใกล้ +1) = พืชพรรณสมบูรณ์
- ค่าต่ำ (ใกล้ −1) = พื้นที่เผา / ดินเปล่า

## 4. dNBR (Delta NBR)

```
dNBR = NBR_pre − NBR_post
```

- **pre** = ช่วงก่อนฤดูเผา (ค่าปริยาย: พ.ย. ปีก่อนหน้า)
- **post** = ช่วงหลังฤดูเผา (ค่าปริยาย: พ.ค. ปีปัจจุบัน)

ใช้ `.median()` ช่วยลดผล cloud/speckle

### dNBR severity thresholds (USGS)

| dNBR | Severity |
|---|---|
| < 0.10 | Unburned |
| 0.10 – 0.27 | Low |
| 0.27 – 0.44 | Moderate-low |
| 0.44 – 0.66 | Moderate-high |
| > 0.66 | High |

ค่าปริยายใน App: **0.27** (moderate) — ผู้ใช้ปรับได้

ที่มา: [Key & Benson 2006, FIREMON Landscape Assessment](https://www.frames.gov/documents/behaveplus/publications/Key_and_Benson-2006-FIREMON.pdf)

## 5. Burn Recurrence

```
recurrence(pixel) = Σ burn_mask(pixel, year)  สำหรับ year ∈ [2015, 2024]
burn_mask(year) = dNBR(year) > threshold  ? 1 : 0
```

ค่าผลลัพธ์: 0 (ไม่เคยเผา) ถึง 10 (เผาทุกปี)

## 6. LST Anomaly (z-score)

**Baseline** (คำนวณต่อ pixel):
```
μ = mean(LST_dry(year))  สำหรับ year ∈ [2015, 2024]
σ = stdDev(LST_dry(year))
```

**Anomaly:**
```
STA(year) = (LST_dry(year) − μ) / σ
```

การตีความ:

| z-score | ความหมาย |
|---|---|
| > +2 | ร้อนผิดปกติมาก |
| +1 ถึง +2 | ร้อนกว่าปกติ |
| −1 ถึง +1 | ปกติ |
| −2 ถึง −1 | เย็นกว่าปกติ |
| < −2 | เย็นผิดปกติมาก |

## 7. Dry Season Window

ในงานนี้กำหนด **ฤดูแล้ง = ธ.ค. (ปีก่อน) – เม.ย. (ปีปัจจุบัน)**

เหตุผล:
- ไทยมีมรสุมตะวันตกเฉียงใต้ พ.ค.–ต.ค. (ฝน)
- ช่วงเผาไร่ / เผาป่าในไทยคือ ก.พ.–เม.ย.
- ค่า LST และอนุมัติ burn scar จึง meaningful ในช่วงนี้มากที่สุด

## 8. FIRMS (Validation)

`FIRMS` ImageCollection จาก NASA MODIS/VIIRS สำหรับ overlay **active fire** เพื่อ cross-check ว่าพื้นที่ที่ App ตรวจจับเป็น burn scar สอดคล้องกับ hotspot ที่ตรวจพบจริงไหม

ข้อจำกัด:
- FIRMS เห็นไฟ **ตอนกำลังลุก** เท่านั้น
- dNBR เห็น scar **หลังไฟดับ** (lag 1–2 สัปดาห์)
- ไฟช่วงกลางคืนบางครั้ง FIRMS จับไม่ได้ถ้าเมฆบัง

## 9. Caveats

1. **dNBR threshold ไม่ universal** — ป่าเต็งรังมี dNBR ต่างจากป่าดิบ ควร calibrate ในพื้นที่จริง
2. **Sensor changes** — Landsat 8 vs 9 TIRS มีความต่างเล็กน้อย (< 0.5°C) ส่วนใหญ่ละเว้นได้
3. **Missing data** — ถ้า pre หรือ post window ไม่มี Landsat pass ที่ไม่มีเมฆ จะไม่มีค่า dNBR สำหรับ pixel นั้น
4. **Baseline 10 ปีสั้น** — ในทาง climatology โดยทั่วไปใช้ 30 ปี แต่ GEE Landsat 8 เริ่ม 2013 และโจทย์จำกัด 10 ปี

## References

1. USGS. "Landsat Collection 2 Level 2 Science Products." [link](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products)
2. Key, C. H., & Benson, N. C. (2006). "Landscape Assessment: Ground measure of severity, the Composite Burn Index; and Remote sensing of severity, the Normalized Burn Ratio."
3. NASA FIRMS. [https://firms.modaps.eosdis.nasa.gov/](https://firms.modaps.eosdis.nasa.gov/)
4. Giglio, L., Schroeder, W., & Justice, C. O. (2016). "The collection 6 MODIS active fire detection algorithm and fire products." *Remote Sensing of Environment, 178*, 31–41.
