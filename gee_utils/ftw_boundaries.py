"""ดึงขอบแปลงเกษตรประเทศไทยจาก Fields of The World (source.coop/ftw/global-data)

ข้อมูล: https://source.coop/ftw/global-data
Schema: fiboa GeoParquet (id, geometry, area, determination_datetime, ...)
"""
from __future__ import annotations

from pathlib import Path

import duckdb

FTW_BASE = "https://data.source.coop/ftw/global-data"

# Thailand bbox (EPSG:4326): lon, lat
TH_BBOX = {"xmin": 97.34, "ymin": 5.61, "xmax": 105.64, "ymax": 20.46}
TH_ISO3 = "THA"


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    return con


def list_files(prefix: str = "") -> list[str]:
    """List .parquet files under ftw/global-data/<prefix>."""
    con = _connect()
    rows = con.execute(
        f"SELECT file FROM glob('{FTW_BASE}/{prefix}**/*.parquet')"
    ).fetchall()
    return [r[0] for r in rows]


def describe(path: str | None = None):
    """Inspect column schema to find the country column.

    Prints (column_name, column_type) rows.
    """
    con = _connect()
    path = path or f"{FTW_BASE}/**/*.parquet"
    return con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{path}') LIMIT 0"
    ).fetchdf()


def load_thailand(
    path: str | None = None,
    country_col: str | None = None,
    use_bbox: bool = True,
    limit: int | None = None,
):
    """โหลดขอบแปลงเฉพาะไทย

    Args:
        path: pattern ของไฟล์ parquet (default = ทุกไฟล์ใน global-data)
        country_col: ชื่อ column ISO-3 ใน dataset (เช่น "country", "iso3")
                     ถ้าไม่ระบุจะ filter ด้วย bbox อย่างเดียว
        use_bbox: filter ด้วย bbox ไทยเพื่อลด I/O (แนะนำ True เสมอ)
        limit: ตัดจำนวนแถว (สำหรับ dev/test)

    Returns:
        GeoDataFrame (EPSG:4326)
    """
    import geopandas as gpd
    from shapely import wkb

    con = _connect()
    path = path or f"{FTW_BASE}/*.parquet"

    where = []
    if country_col:
        where.append(f"{country_col} = '{TH_ISO3}'")
    if use_bbox:
        # fiboa geoparquet มี struct `bbox` ช่วย pushdown filter โดยไม่ decode geometry
        b = TH_BBOX
        where.append(
            f"bbox.xmin >= {b['xmin']} AND bbox.xmax <= {b['xmax']} "
            f"AND bbox.ymin >= {b['ymin']} AND bbox.ymax <= {b['ymax']}"
        )
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit_sql = f"LIMIT {limit}" if limit else ""

    # geometry ใน GeoParquet/fiboa เก็บเป็น WKB bytes อยู่แล้ว อ่านตรงได้
    sql = f"""
        SELECT *
        FROM read_parquet('{path}', hive_partitioning=true)
        {where_sql}
        {limit_sql}
    """
    df = con.execute(sql).fetchdf()
    df["geometry"] = df["geometry"].apply(lambda b: wkb.loads(bytes(b)))
    return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")


def save(gdf, out_dir: str | Path, name: str = "thailand_fields") -> dict[str, Path]:
    """Save เป็น GeoParquet (หลัก) + GeoJSON (สำหรับ GEE import)"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "parquet": out_dir / f"{name}.parquet",
        "geojson": out_dir / f"{name}.geojson",
    }
    gdf.to_parquet(paths["parquet"])
    gdf.to_file(paths["geojson"], driver="GeoJSON")
    return paths


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Download FTW field boundaries for Thailand")
    p.add_argument("-o", "--out", default="data/ftw", help="output folder")
    p.add_argument("--country-col", default=None, help="ISO-3 column name (if present)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--inspect", action="store_true", help="print schema then exit")
    args = p.parse_args()

    if args.inspect:
        print(describe().to_string(index=False))
        raise SystemExit(0)

    print("Loading Thailand fields from FTW global-data ...")
    gdf = load_thailand(country_col=args.country_col, limit=args.limit)
    print(f"  fetched {len(gdf):,} polygons")
    paths = save(gdf, args.out)
    for k, v in paths.items():
        print(f"  wrote {k}: {v}")
