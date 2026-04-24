"""โหลดและประมวลผล Landsat 8/9 Collection 2 Level 2"""
from __future__ import annotations

import ee

from .constants import DRY_END_MONTH, DRY_START_MONTH


def mask_landsat_c2(img: ee.Image) -> ee.Image:
    """Mask cloud, shadow, snow จาก QA_PIXEL (bit 1/3/4/5) + QA_RADSAT"""
    qa = img.select("QA_PIXEL")
    mask = (
        qa.bitwiseAnd(1 << 1).eq(0)
        .And(qa.bitwiseAnd(1 << 3).eq(0))
        .And(qa.bitwiseAnd(1 << 4).eq(0))
        .And(qa.bitwiseAnd(1 << 5).eq(0))
    )
    sat_mask = img.select("QA_RADSAT").eq(0)
    return img.updateMask(mask).updateMask(sat_mask)


def apply_scale_factors(img: ee.Image) -> ee.Image:
    """scale SR และ ST ให้เป็นค่าจริง (°C)"""
    optical = img.select("SR_B.").multiply(0.0000275).add(-0.2)
    thermal = (
        img.select("ST_B10")
        .multiply(0.00341802)
        .add(149.0)
        .subtract(273.15)
        .rename("LST")
    )
    return img.addBands(optical, None, True).addBands(thermal, None, True)


def load_landsat(start: ee.Date, end: ee.Date, aoi: ee.Geometry) -> ee.ImageCollection:
    """โหลด Landsat 8 + 9 merged, cloud-masked, scaled"""
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
    return (
        l8.merge(l9)
        .filterBounds(aoi)
        .filterDate(start, end)
        .map(mask_landsat_c2)
        .map(apply_scale_factors)
    )


def add_nbr(img: ee.Image) -> ee.Image:
    """NBR = (NIR − SWIR2) / (NIR + SWIR2)"""
    nbr = img.normalizedDifference(["SR_B5", "SR_B7"]).rename("NBR")
    return img.addBands(nbr)


def lst_dry_season(year: int, aoi: ee.Geometry) -> ee.Image:
    """LST เฉลี่ยฤดูแล้ง (ธ.ค. ปีก่อน – เม.ย. ปีปัจจุบัน)"""
    y = ee.Number(year)
    start = ee.Date.fromYMD(y.subtract(1), DRY_START_MONTH, 1)
    end = ee.Date.fromYMD(y, DRY_END_MONTH + 1, 1)
    col = load_landsat(start, end, aoi)
    return (
        col.select("LST")
        .mean()
        .set("year", y)
        .set("system:time_start", ee.Date.fromYMD(y, 1, 1).millis())
    )
