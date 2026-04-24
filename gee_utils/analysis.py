"""ฟังก์ชันวิเคราะห์: dNBR, burn recurrence, LST anomaly, Dynamic World"""
from __future__ import annotations

from typing import Dict

import ee

from .constants import NORTHERN_PROVINCES, YEARS
from .landsat import add_nbr, load_landsat, lst_dry_season


def get_aoi() -> ee.FeatureCollection:
    """AOI = 9 จังหวัดภาคเหนือ"""
    gaul = ee.FeatureCollection("FAO/GAUL/2015/level1")
    return (
        gaul.filter(ee.Filter.eq("ADM0_NAME", "Thailand"))
        .filter(ee.Filter.inList("ADM1_NAME", NORTHERN_PROVINCES))
    )


def get_province(eng_name: str) -> ee.FeatureCollection:
    gaul = ee.FeatureCollection("FAO/GAUL/2015/level1")
    return gaul.filter(ee.Filter.eq("ADM1_NAME", eng_name))


def dnbr_year(
    year: int, pre_month: int, post_month: int, aoi: ee.Geometry
) -> ee.Image:
    """dNBR = NBR_pre − NBR_post"""
    y = ee.Number(year)
    pre_start = ee.Date.fromYMD(y.subtract(1), pre_month, 1)
    pre_end = pre_start.advance(30, "day")
    post_start = ee.Date.fromYMD(y, post_month, 1)
    post_end = post_start.advance(30, "day")

    pre = load_landsat(pre_start, pre_end, aoi).map(add_nbr).select("NBR").median()
    post = load_landsat(post_start, post_end, aoi).map(add_nbr).select("NBR").median()
    return pre.subtract(post).rename("dNBR").set("year", y)


def burn_mask_year(
    year: int, pre_month: int, post_month: int, threshold: float, aoi: ee.Geometry
) -> ee.Image:
    """Binary mask: dNBR > threshold"""
    return (
        dnbr_year(year, pre_month, post_month, aoi)
        .gt(threshold)
        .rename("burned")
        .set("year", year)
        .set("system:time_start", ee.Date.fromYMD(year, 1, 1).millis())
    )


def burn_recurrence(
    pre_month: int, post_month: int, threshold: float, aoi: ee.Geometry
) -> ee.Image:
    """Recurrence count 2015–2024"""
    imgs = [
        burn_mask_year(y, pre_month, post_month, threshold, aoi) for y in YEARS
    ]
    return ee.ImageCollection(imgs).sum().rename("recurrence")


def lst_baseline(aoi: ee.Geometry) -> Dict[str, ee.Image]:
    imgs = [lst_dry_season(y, aoi) for y in YEARS]
    col = ee.ImageCollection(imgs)
    return {
        "mean": col.mean().rename("LST_mean"),
        "std": col.reduce(ee.Reducer.stdDev()).rename("LST_std"),
        "collection": col,
    }


def lst_anomaly(
    year: int, baseline: Dict[str, ee.Image], aoi: ee.Geometry
) -> ee.Image:
    lst = lst_dry_season(year, aoi)
    return (
        lst.subtract(baseline["mean"])
        .divide(baseline["std"])
        .rename("STA")
        .set("year", year)
    )


def dynamic_world_year(year: int, aoi: ee.Geometry) -> ee.Image:
    """Dynamic World LULC mode ของปีที่ระบุ (10 m)"""
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    dw = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(aoi)
        .filterDate(start, end)
        .select("label")
    )
    return dw.reduce(ee.Reducer.mode()).rename("landcover").set("year", year)


# ---- สถิติรวม (ใช้ใน Analytics page) ----


def burned_area_per_year(
    pre_month: int, post_month: int, threshold: float, aoi: ee.Geometry
) -> ee.FeatureCollection:
    """คำนวณพื้นที่เผา (km²) ของแต่ละปี"""

    def _per_year(y):
        mask = burn_mask_year(y, pre_month, post_month, threshold, aoi)
        area = (
            mask.multiply(ee.Image.pixelArea())
            .divide(1e6)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=aoi,
                scale=90,
                maxPixels=1e13,
                bestEffort=True,
            )
            .get("burned")
        )
        return ee.Feature(None, {"year": y, "area_km2": area})

    return ee.FeatureCollection([_per_year(y) for y in YEARS])


def lst_anomaly_mean_per_year(aoi: ee.Geometry) -> ee.FeatureCollection:
    """ค่าเฉลี่ย STA ต่อปีทั้ง AOI"""
    baseline = lst_baseline(aoi)

    def _per_year(y):
        sta = lst_anomaly(y, baseline, aoi)
        mean = sta.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=120,
            maxPixels=1e13,
            bestEffort=True,
        ).get("STA")
        return ee.Feature(None, {"year": y, "sta_mean": mean})

    return ee.FeatureCollection([_per_year(y) for y in YEARS])


def recurrence_histogram(
    pre_month: int, post_month: int, threshold: float, aoi: ee.Geometry
) -> ee.Dictionary:
    """นับจำนวน pixel ในแต่ละระดับ recurrence (0–10)"""
    rec = burn_recurrence(pre_month, post_month, threshold, aoi)
    return rec.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=aoi,
        scale=90,
        maxPixels=1e13,
        bestEffort=True,
    ).get("recurrence")


def recurrence_by_province(
    pre_month: int, post_month: int, threshold: float
) -> ee.FeatureCollection:
    """หาพื้นที่เผาซ้ำ (≥3 ครั้ง) ต่อจังหวัด — เรียงจากมากไปน้อย"""
    aoi = get_aoi()
    rec = burn_recurrence(pre_month, post_month, threshold, aoi)
    recurrent = rec.gte(3).rename("recurrent_mask")
    area_img = recurrent.multiply(ee.Image.pixelArea()).divide(1e6)

    def _per_prov(f):
        area = area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=f.geometry(),
            scale=90,
            maxPixels=1e13,
            bestEffort=True,
        ).get("recurrent_mask")
        return f.set("recurrent_km2", area)

    return aoi.map(_per_prov).sort("recurrent_km2", False)


def landcover_of_recurrent_burn(
    pre_month: int,
    post_month: int,
    threshold: float,
    year: int,
    aoi: ee.Geometry,
) -> ee.Dictionary:
    """Dynamic World land cover ของพื้นที่เผาซ้ำ (≥3 ครั้ง)"""
    rec = burn_recurrence(pre_month, post_month, threshold, aoi)
    recurrent_mask = rec.gte(3)
    dw = dynamic_world_year(year, aoi).updateMask(recurrent_mask)
    return dw.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=aoi,
        scale=30,
        maxPixels=1e13,
        bestEffort=True,
    ).get("landcover")
