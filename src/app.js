/**
 * ========================================================================
 *  วิเคราะห์พื้นที่เผาซ้ำซากและความผิดปกติของอุณหภูมิผิวดิน
 *  ภาคเหนือของประเทศไทย (2015–2024)
 *
 *  Data : Landsat 8/9 Collection 2 Level 2 (SR + ST)
 *  Method : LST Anomaly (z-score) + dNBR Burn Recurrence
 *  Output : Google Earth Engine App (UI แบบโต้ตอบได้)
 *
 *  วิธีใช้: คัดลอกทั้งไฟล์ไปวางใน GEE Code Editor แล้วกด Run
 *          จากนั้นกด Apps > Publish เพื่อเผยแพร่เป็น App
 * ========================================================================
 */

// ---------- 1. ค่าคงที่และ AOI -----------------------------------------

var NORTHERN_PROVINCES = [
  'Chiang Mai', 'Chiang Rai', 'Mae Hong Son', 'Lampang', 'Lamphun',
  'Nan', 'Phayao', 'Phrae', 'Uttaradit'
];

var PROVINCE_TH = {
  'Chiang Mai': 'เชียงใหม่',
  'Chiang Rai': 'เชียงราย',
  'Mae Hong Son': 'แม่ฮ่องสอน',
  'Lampang': 'ลำปาง',
  'Lamphun': 'ลำพูน',
  'Nan': 'น่าน',
  'Phayao': 'พะเยา',
  'Phrae': 'แพร่',
  'Uttaradit': 'อุตรดิตถ์'
};

var gaul1 = ee.FeatureCollection('FAO/GAUL/2015/level1');
var northernThailand = gaul1
  .filter(ee.Filter.eq('ADM0_NAME', 'Thailand'))
  .filter(ee.Filter.inList('ADM1_NAME', NORTHERN_PROVINCES));

var YEARS = ee.List.sequence(2015, 2024);

// ฤดูแล้งไทย: ธ.ค. (ปีก่อน) – เม.ย. (ปีปัจจุบัน)
var DRY_START_MONTH = 12;
var DRY_END_MONTH = 4;

// Palette
var PAL_RECURRENCE = ['#ffffb2','#fed976','#feb24c','#fd8d3c','#fc4e2a','#e31a1c','#b10026'];
var PAL_ANOMALY = ['#2c7bb6','#abd9e9','#ffffbf','#fdae61','#d7191c'];
var PAL_DNBR = ['#1a9850','#ffffbf','#fdae61','#d73027','#7f0000'];


// ---------- 2. Cloud masking & preprocessing --------------------------

/**
 * Mask cloud, shadow, snow จาก QA_PIXEL ของ Landsat C2 L2
 * bit 3=cloud, 4=cloud shadow, 5=snow, 1=dilated cloud
 */
function maskLandsatC2(img) {
  var qa = img.select('QA_PIXEL');
  var mask = qa.bitwiseAnd(1 << 1).eq(0)
    .and(qa.bitwiseAnd(1 << 3).eq(0))
    .and(qa.bitwiseAnd(1 << 4).eq(0))
    .and(qa.bitwiseAnd(1 << 5).eq(0));
  var satMask = img.select('QA_RADSAT').eq(0);
  return img.updateMask(mask).updateMask(satMask);
}

/**
 * แปลง scale factor เป็นค่าจริง: SR (reflectance) และ ST (°C)
 */
function applyScaleFactors(img) {
  var optical = img.select('SR_B.').multiply(0.0000275).add(-0.2);
  var thermal = img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15);
  return img.addBands(optical, null, true)
            .addBands(thermal.rename('LST'), null, true);
}

/**
 * โหลด Landsat 8 + 9 ของภาคเหนือในช่วงเวลาที่กำหนด
 */
function loadLandsat(startDate, endDate) {
  var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2');
  var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2');
  return l8.merge(l9)
    .filterBounds(northernThailand)
    .filterDate(startDate, endDate)
    .map(maskLandsatC2)
    .map(applyScaleFactors);
}

/**
 * คำนวณ NBR: (NIR − SWIR2) / (NIR + SWIR2)
 * Landsat 8/9: NIR = SR_B5, SWIR2 = SR_B7
 */
function addNBR(img) {
  var nbr = img.normalizedDifference(['SR_B5', 'SR_B7']).rename('NBR');
  return img.addBands(nbr);
}


// ---------- 3. ฟังก์ชันวิเคราะห์รายปี ---------------------------------

/**
 * LST เฉลี่ยฤดูแล้งสำหรับปีที่กำหนด
 * @param {Number} year   เช่น 2020 → ใช้ Dec 2019 – Apr 2020
 */
function lstDrySeason(year) {
  year = ee.Number(year);
  var start = ee.Date.fromYMD(year.subtract(1), DRY_START_MONTH, 1);
  var end = ee.Date.fromYMD(year, DRY_END_MONTH + 1, 1);
  var col = loadLandsat(start, end);
  return col.select('LST').mean()
    .set('year', year)
    .set('system:time_start', ee.Date.fromYMD(year, 1, 1).millis());
}

/**
 * คำนวณ dNBR สำหรับปีที่กำหนด
 * pre  = ช่วงก่อนฤดูเผา
 * post = ช่วงหลังฤดูเผา
 * ผู้ใช้ปรับเดือน pre/post ผ่าน UI ได้
 */
function dNBRYear(year, preMonth, postMonth) {
  year = ee.Number(year);
  var preStart = ee.Date.fromYMD(year.subtract(1), preMonth, 1);
  var preEnd = preStart.advance(30, 'day');
  var postStart = ee.Date.fromYMD(year, postMonth, 1);
  var postEnd = postStart.advance(30, 'day');

  var pre = loadLandsat(preStart, preEnd).map(addNBR).select('NBR').median();
  var post = loadLandsat(postStart, postEnd).map(addNBR).select('NBR').median();
  return pre.subtract(post).rename('dNBR')
    .set('year', year);
}

/**
 * burn mask รายปี (dNBR > threshold)
 */
function burnMaskYear(year, preMonth, postMonth, threshold) {
  return dNBRYear(year, preMonth, postMonth)
    .gt(threshold)
    .rename('burned')
    .set('year', year);
}

/**
 * Recurrence = sum ของ burn mask ทุกปี (0–10)
 */
function burnRecurrence(preMonth, postMonth, threshold) {
  var col = ee.ImageCollection(YEARS.map(function (y) {
    return burnMaskYear(y, preMonth, postMonth, threshold);
  }));
  return col.sum().rename('recurrence');
}

/**
 * LST baseline (μ, σ) จาก 10 ปี
 */
function lstBaseline() {
  var col = ee.ImageCollection(YEARS.map(lstDrySeason));
  return {
    mean: col.mean().rename('LST_mean'),
    std: col.reduce(ee.Reducer.stdDev()).rename('LST_std'),
    collection: col
  };
}

/**
 * STA z-score สำหรับปีเดียว
 */
function lstAnomaly(year, baseline) {
  var lst = lstDrySeason(year);
  return lst.subtract(baseline.mean)
    .divide(baseline.std)
    .rename('STA')
    .set('year', year);
}


// ---------- 4. UI -----------------------------------------------------

ui.root.clear();

var mapPanel = ui.Map();
mapPanel.setOptions('HYBRID');
mapPanel.centerObject(northernThailand, 7);
mapPanel.style().set('cursor', 'crosshair');

// --- State ---
var state = {
  year: 2024,
  province: 'ทั้งภาคเหนือ',
  preMonth: 11,
  postMonth: 5,
  dnbrThreshold: 0.27,
  activeLayer: 'recurrence',
  opacity: 0.75
};

var baseline = lstBaseline();

// --- Control Panel ---
var controlPanel = ui.Panel({
  style: {width: '340px', padding: '12px', backgroundColor: '#fafafa'}
});

controlPanel.add(ui.Label('🔥 วิเคราะห์พื้นที่เผาซ้ำซาก', {
  fontSize: '18px', fontWeight: 'bold', margin: '0 0 4px 0'
}));
controlPanel.add(ui.Label('ภาคเหนือของประเทศไทย · 2015–2024', {
  fontSize: '12px', color: '#666', margin: '0 0 12px 0'
}));

// --- จังหวัด ---
controlPanel.add(ui.Label('📍 พื้นที่ศึกษา', {fontWeight: 'bold', margin: '8px 0 4px 0'}));
var provinceSelect = ui.Select({
  items: ['ทั้งภาคเหนือ'].concat(NORTHERN_PROVINCES.map(function (p) {
    return PROVINCE_TH[p];
  })),
  value: 'ทั้งภาคเหนือ',
  onChange: function (val) {
    state.province = val;
    zoomToProvince(val);
  },
  style: {stretch: 'horizontal'}
});
controlPanel.add(provinceSelect);

// --- ปี ---
controlPanel.add(ui.Label('📅 ปีที่ต้องการดู (สำหรับ Anomaly/dNBR)', {
  fontWeight: 'bold', margin: '12px 0 4px 0'
}));
var yearSlider = ui.Slider({
  min: 2015, max: 2024, value: 2024, step: 1,
  onChange: function (val) { state.year = val; redrawLayer(); },
  style: {stretch: 'horizontal'}
});
controlPanel.add(yearSlider);

// --- Layer switch ---
controlPanel.add(ui.Label('🗺️ เลเยอร์ที่แสดง', {
  fontWeight: 'bold', margin: '12px 0 4px 0'
}));
var layerSelect = ui.Select({
  items: [
    {label: 'พื้นที่เผาซ้ำ (10 ปี)', value: 'recurrence'},
    {label: 'LST Anomaly (z-score)', value: 'anomaly'},
    {label: 'dNBR รายปี', value: 'dnbr'},
    {label: 'LST ฤดูแล้ง (°C)', value: 'lst'}
  ],
  value: 'recurrence',
  onChange: function (val) { state.activeLayer = val; redrawLayer(); },
  style: {stretch: 'horizontal'}
});
controlPanel.add(layerSelect);

// --- dNBR threshold ---
controlPanel.add(ui.Label('🎚️ dNBR threshold (เผา)', {
  fontWeight: 'bold', margin: '12px 0 4px 0'
}));
controlPanel.add(ui.Label(
  '0.10=low · 0.27=moderate · 0.44=high · 0.66=severe',
  {fontSize: '11px', color: '#888', margin: '0 0 4px 0'}
));
var thresholdSlider = ui.Slider({
  min: 0.1, max: 0.8, value: 0.27, step: 0.01,
  onChange: function (val) { state.dnbrThreshold = val; redrawLayer(); },
  style: {stretch: 'horizontal'}
});
controlPanel.add(thresholdSlider);

// --- Pre/Post fire months ---
controlPanel.add(ui.Label('📆 ช่วงเดือนเปรียบเทียบ (dNBR)', {
  fontWeight: 'bold', margin: '12px 0 4px 0'
}));
var preLabel = ui.Label('ก่อนไฟ (ปีก่อนหน้า): เดือน 11', {fontSize: '12px'});
controlPanel.add(preLabel);
var preSlider = ui.Slider({
  min: 9, max: 12, value: 11, step: 1,
  onChange: function (val) {
    state.preMonth = val;
    preLabel.setValue('ก่อนไฟ (ปีก่อนหน้า): เดือน ' + val);
    redrawLayer();
  },
  style: {stretch: 'horizontal'}
});
controlPanel.add(preSlider);

var postLabel = ui.Label('หลังไฟ (ปีปัจจุบัน): เดือน 5', {fontSize: '12px'});
controlPanel.add(postLabel);
var postSlider = ui.Slider({
  min: 4, max: 7, value: 5, step: 1,
  onChange: function (val) {
    state.postMonth = val;
    postLabel.setValue('หลังไฟ (ปีปัจจุบัน): เดือน ' + val);
    redrawLayer();
  },
  style: {stretch: 'horizontal'}
});
controlPanel.add(postSlider);

// --- Opacity ---
controlPanel.add(ui.Label('🔳 ความโปร่งใสของเลเยอร์', {
  fontWeight: 'bold', margin: '12px 0 4px 0'
}));
var opacitySlider = ui.Slider({
  min: 0, max: 1, value: 0.75, step: 0.05,
  onChange: function (val) {
    state.opacity = val;
    var layers = mapPanel.layers();
    for (var i = 0; i < layers.length(); i++) {
      var l = layers.get(i);
      if (l.getName() !== 'ขอบเขตจังหวัด') l.setOpacity(val);
    }
  },
  style: {stretch: 'horizontal'}
});
controlPanel.add(opacitySlider);

// --- Legend placeholder ---
var legendPanel = ui.Panel({
  style: {padding: '8px', margin: '12px 0 0 0', backgroundColor: '#ffffff'}
});
controlPanel.add(legendPanel);

// --- Chart panel ---
var chartPanel = ui.Panel({style: {margin: '12px 0 0 0'}});
controlPanel.add(chartPanel);

// --- About ---
controlPanel.add(ui.Label('ℹ️ คำอธิบาย', {
  fontWeight: 'bold', margin: '16px 0 4px 0'
}));
controlPanel.add(ui.Label(
  '• คลิกบนแผนที่เพื่อดูกราฟ LST ย้อนหลัง 10 ปี\n' +
  '• dNBR = NBR ก่อนไฟ − NBR หลังไฟ (ค่าสูงบ่งบอกการเผาไหม้รุนแรง)\n' +
  '• STA z-score: +2 = ร้อนผิดปกติ, −2 = เย็นผิดปกติ\n' +
  '• Baseline คำนวณจากค่าเฉลี่ย LST ฤดูแล้ง 10 ปี',
  {fontSize: '11px', color: '#555', whiteSpace: 'pre'}
));

ui.root.add(controlPanel);
ui.root.add(mapPanel);


// ---------- 5. Layer rendering ---------------------------------------

function redrawLayer() {
  mapPanel.layers().reset();

  // ขอบเขตจังหวัด
  var outline = ee.Image().byte()
    .paint({featureCollection: northernThailand, color: 1, width: 2});
  mapPanel.addLayer(outline, {min: 0, max: 1, palette: ['00000000', '#ffffff']}, 'ขอบเขตจังหวัด');

  if (state.activeLayer === 'recurrence') {
    var rec = burnRecurrence(state.preMonth, state.postMonth, state.dnbrThreshold)
      .clip(northernThailand);
    var masked = rec.updateMask(rec.gt(0));
    mapPanel.addLayer(masked, {
      min: 1, max: 10, palette: PAL_RECURRENCE
    }, 'พื้นที่เผาซ้ำ (ครั้ง)', true, state.opacity);
    updateLegend('recurrence');

  } else if (state.activeLayer === 'anomaly') {
    var sta = lstAnomaly(state.year, baseline).clip(northernThailand);
    mapPanel.addLayer(sta, {
      min: -3, max: 3, palette: PAL_ANOMALY
    }, 'LST Anomaly ' + state.year, true, state.opacity);
    updateLegend('anomaly');

  } else if (state.activeLayer === 'dnbr') {
    var dnbr = dNBRYear(state.year, state.preMonth, state.postMonth)
      .clip(northernThailand);
    mapPanel.addLayer(dnbr, {
      min: -0.2, max: 0.8, palette: PAL_DNBR
    }, 'dNBR ' + state.year, true, state.opacity);
    updateLegend('dnbr');

  } else if (state.activeLayer === 'lst') {
    var lst = lstDrySeason(state.year).clip(northernThailand);
    mapPanel.addLayer(lst, {
      min: 20, max: 45, palette: PAL_ANOMALY
    }, 'LST ฤดูแล้ง ' + state.year + ' (°C)', true, state.opacity);
    updateLegend('lst');
  }

  // FIRMS active fire (overlay ตลอด)
  var firms = ee.ImageCollection('FIRMS')
    .filterDate(
      ee.Date.fromYMD(state.year, 1, 1),
      ee.Date.fromYMD(state.year, 12, 31)
    )
    .select('T21')
    .max()
    .clip(northernThailand);
  mapPanel.addLayer(firms, {
    min: 325, max: 400, palette: ['red', 'orange', 'yellow']
  }, 'FIRMS Active Fire ' + state.year, false, 0.8);
}


// ---------- 6. Legend -------------------------------------------------

function updateLegend(type) {
  legendPanel.clear();

  var title;
  var palette;
  var min;
  var max;

  if (type === 'recurrence') {
    title = 'จำนวนครั้งที่เผา (2015–2024)';
    palette = PAL_RECURRENCE;
    min = 1; max = 10;
  } else if (type === 'anomaly') {
    title = 'LST Anomaly (z-score)';
    palette = PAL_ANOMALY;
    min = -3; max = 3;
  } else if (type === 'dnbr') {
    title = 'dNBR';
    palette = PAL_DNBR;
    min = -0.2; max = 0.8;
  } else {
    title = 'LST (°C)';
    palette = PAL_ANOMALY;
    min = 20; max = 45;
  }

  legendPanel.add(ui.Label(title, {fontWeight: 'bold', fontSize: '12px'}));

  var lon = ee.Image.pixelLonLat().select('longitude');
  var gradient = lon.multiply((max - min) / 100.0).add(min);
  var legendImage = gradient.visualize({min: min, max: max, palette: palette});

  var thumbnail = ui.Thumbnail({
    image: legendImage,
    params: {bbox: '0,0,100,8', dimensions: '200x15'},
    style: {stretch: 'horizontal', margin: '4px 0'}
  });
  legendPanel.add(thumbnail);

  var labels = ui.Panel({
    widgets: [
      ui.Label(String(min), {margin: '0', fontSize: '10px'}),
      ui.Label(String((min + max) / 2), {margin: '0 auto', fontSize: '10px'}),
      ui.Label(String(max), {margin: '0', fontSize: '10px'})
    ],
    layout: ui.Panel.Layout.flow('horizontal'),
    style: {stretch: 'horizontal'}
  });
  legendPanel.add(labels);
}


// ---------- 7. Province zoom -----------------------------------------

function zoomToProvince(thaiName) {
  if (thaiName === 'ทั้งภาคเหนือ') {
    mapPanel.centerObject(northernThailand, 7);
    return;
  }
  var engName = null;
  for (var key in PROVINCE_TH) {
    if (PROVINCE_TH[key] === thaiName) engName = key;
  }
  if (engName) {
    var prov = gaul1.filter(ee.Filter.eq('ADM1_NAME', engName));
    mapPanel.centerObject(prov, 9);
  }
}


// ---------- 8. Click → LST time series chart -------------------------

mapPanel.onClick(function (coords) {
  chartPanel.clear();
  var pt = ee.Geometry.Point([coords.lon, coords.lat]);

  chartPanel.add(ui.Label('📊 กำลังโหลดกราฟ...', {fontSize: '12px'}));

  var lstCol = baseline.collection.map(function (img) {
    return img.set('year', img.get('year'));
  });

  var chart = ui.Chart.image.series({
    imageCollection: lstCol,
    region: pt,
    reducer: ee.Reducer.mean(),
    scale: 30,
    xProperty: 'system:time_start'
  }).setOptions({
    title: 'LST ฤดูแล้งที่จุด (' +
      coords.lon.toFixed(3) + ', ' + coords.lat.toFixed(3) + ')',
    vAxis: {title: '°C'},
    hAxis: {title: 'ปี', format: 'yyyy'},
    lineWidth: 2,
    pointSize: 4,
    colors: ['#d73027']
  });

  chartPanel.clear();
  chartPanel.add(chart);
});


// ---------- 9. Init ---------------------------------------------------

redrawLayer();

print('✅ แอปพร้อมใช้งาน — คลิกบนแผนที่เพื่อดู time-series');
print('Baseline mean LST:', baseline.mean);
print('AOI:', northernThailand);
