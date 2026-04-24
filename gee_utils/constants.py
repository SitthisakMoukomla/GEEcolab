"""ค่าคงที่ที่ใช้ทั่วทั้งแอป"""

NORTHERN_PROVINCES = [
    'Chiang Mai', 'Chiang Rai', 'Mae Hong Son', 'Lampang', 'Lamphun',
    'Nan', 'Phayao', 'Phrae', 'Uttaradit'
]

PROVINCE_TH = {
    'Chiang Mai': 'เชียงใหม่',
    'Chiang Rai': 'เชียงราย',
    'Mae Hong Son': 'แม่ฮ่องสอน',
    'Lampang': 'ลำปาง',
    'Lamphun': 'ลำพูน',
    'Nan': 'น่าน',
    'Phayao': 'พะเยา',
    'Phrae': 'แพร่',
    'Uttaradit': 'อุตรดิตถ์'
}

PROVINCE_EN = {v: k for k, v in PROVINCE_TH.items()}

YEARS = list(range(2015, 2025))

DRY_START_MONTH = 12
DRY_END_MONTH = 4

PAL_RECURRENCE = ['#ffffb2', '#fed976', '#feb24c', '#fd8d3c',
                  '#fc4e2a', '#e31a1c', '#b10026']
PAL_ANOMALY = ['#2c7bb6', '#abd9e9', '#ffffbf', '#fdae61', '#d7191c']
PAL_DNBR = ['#1a9850', '#ffffbf', '#fdae61', '#d73027', '#7f0000']
PAL_LST = ['#313695', '#74add1', '#ffffbf', '#f46d43', '#a50026']

DW_CLASS_NAMES = [
    'water', 'trees', 'grass', 'flooded_vegetation', 'crops',
    'shrub_and_scrub', 'built', 'bare', 'snow_and_ice'
]

DW_CLASS_TH = {
    'water': 'แหล่งน้ำ',
    'trees': 'ป่าไม้',
    'grass': 'ทุ่งหญ้า',
    'flooded_vegetation': 'พืชน้ำ',
    'crops': 'พื้นที่เกษตร',
    'shrub_and_scrub': 'ไม้พุ่ม',
    'built': 'พื้นที่สิ่งปลูกสร้าง',
    'bare': 'พื้นที่เปล่า',
    'snow_and_ice': 'หิมะ/น้ำแข็ง'
}

DW_PALETTE = [
    '#419BDF', '#397D49', '#88B053', '#7A87C6', '#E49635',
    '#DFC35A', '#C4281B', '#A59B8F', '#B39FE1'
]
