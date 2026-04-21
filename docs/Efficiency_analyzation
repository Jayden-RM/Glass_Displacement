# note: THis was used in apps scripts to help with formatting the data in google sheets. Generates efficiency, Hysteris index, ect for all samples
# change the folderId to match the folder in your google drive that contains the raw data files ( in this same folder is an example of what that csv looks like)



function importCsvsMakeTabsOverlayAndMetrics() {
  const folderId = '1v6F-uFLG4paxN4GdOHg_HP2ZE6qPcgXj';
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const folder = DriveApp.getFolderById(folderId);
  const files = folder.getFiles();

  const overlaySheetName = 'Overlay_All_IV';
  const summarySheetName = 'IV_Summary';

  // Create / reset overlay + summary sheets
  let overlaySheet = ss.getSheetByName(overlaySheetName);
  if (!overlaySheet) overlaySheet = ss.insertSheet(overlaySheetName);
  else overlaySheet.clear();

  let summarySheet = ss.getSheetByName(summarySheetName);
  if (!summarySheet) summarySheet = ss.insertSheet(summarySheetName);
  else summarySheet.clear();

  overlaySheet.getCharts().forEach(chart => overlaySheet.removeChart(chart));
  summarySheet.getCharts().forEach(chart => summarySheet.removeChart(chart));

  const summaryRows = [[
    'Sample',
    'Direction',
    'Sheet Name',
    'Jsc',
    'Voc',
    'Vmpp',
    'Jmpp',
    'Pmax Density',
    'Efficiency (%)'
  ]];

  const pairedMetrics = {}; // store fwd/rev metrics for hysteresis calculation

  let overlayCol = 1; // start in col A

  while (files.hasNext()) {
    const file = files.next();
    const fileName = file.getName();

    if (!fileName.toLowerCase().endsWith('.csv')) continue;

    const csvText = file.getBlob().getDataAsString();
    const data = Utilities.parseCsv(csvText);
    if (!data || data.length < 2) continue;

    const rawName = fileName.replace(/\.csv$/i, '');
    const sheetName = makeValidSheetName_(rawName);

    // Make or reset individual sheet
    let sheet = ss.getSheetByName(sheetName);
    if (!sheet) sheet = ss.insertSheet(sheetName);
    else sheet.clear();

    sheet.getCharts().forEach(chart => sheet.removeChart(chart));

    // Write CSV
    sheet.getRange(1, 1, data.length, data[0].length).setValues(data);

    const headers = data[0];
    const rows = data.slice(1);

    const voltageCol = findColumnIndex_(headers, ['# Volts', 'Volts', 'Voltage', 'V']);
    const currentCol = findColumnIndex_(headers, ['Current', 'I']);
    const jCol = findColumnIndex_(headers, ['J', 'Current Density', 'Jsc']);

    if (voltageCol === -1 || (currentCol === -1 && jCol === -1)) continue;

    // Build per-sheet chart from Voltage vs Current Density if available, else Current
    const yCol = (jCol !== -1) ? jCol + 1 : currentCol + 1;
    const xCol = voltageCol + 1;

    const chart = sheet.newChart()
      .setChartType(Charts.ChartType.LINE)
      .addRange(sheet.getRange(1, xCol, data.length, 1))
      .addRange(sheet.getRange(1, yCol, data.length, 1))
      .setPosition(1, Math.max(headers.length + 2, 5), 0, 0)
      .setOption('title', sheetName)
      .setOption('legend', { position: 'right' })
      .setOption('hAxis', { title: headers[voltageCol] })
      .setOption('vAxis', { title: headers[yCol - 1] })
      .build();

    sheet.insertChart(chart);

    // Copy voltage + chosen y data into overlay sheet
    const overlayHeader1 = sheetName + ' Voltage';
    const overlayHeader2 = sheetName + ' ' + headers[yCol - 1];
    overlaySheet.getRange(1, overlayCol, 1, 2).setValues([[overlayHeader1, overlayHeader2]]);

    const overlayData = rows.map(r => [
      safeNumber_(r[voltageCol]),
      safeNumber_(r[yCol - 1])
    ]);
    overlaySheet.getRange(2, overlayCol, overlayData.length, 2).setValues(overlayData);

    // Metrics
    const parsed = rows.map(r => ({
      vRaw: safeNumber_(r[voltageCol]),
      v: normalizeVoltage_(safeNumber_(r[voltageCol])), // auto-convert if mV-like
      current: currentCol !== -1 ? safeNumber_(r[currentCol]) : null,
      j: jCol !== -1 ? safeNumber_(r[jCol]) : null
    })).filter(r => !isNaN(r.v));

    const metrics = extractIvMetrics_(parsed);

    const lowerName = fileName.toLowerCase();

    const direction =
      lowerName.includes('_fwd_') ? 'fwd' :
      lowerName.includes('_rev_') ? 'rev' : 'unknown';

    const baseSample = fileName
      .replace(/\.csv$/i, '')
      .replace(/_(fwd|rev)_IV(?:_after|_before|_\d+)?$/i, '');
 

    summaryRows.push([
      baseSample,
      direction,
      sheetName,
      metrics.jsc,
      metrics.voc,
      metrics.vmpp,
      metrics.jmpp,
      metrics.pmaxDensity,
      metrics.efficiency
    ]);

    if (!pairedMetrics[baseSample]) pairedMetrics[baseSample] = {};
    pairedMetrics[baseSample][direction] = metrics;

    overlayCol += 2;
  }

  // Write summary base metrics
  summarySheet.getRange(1, 1, summaryRows.length, summaryRows[0].length).setValues(summaryRows);

  // Add hysteresis section
  const startRow = summaryRows.length + 3;
  const hysteresisRows = [[
    'Sample',
    'Eff_fwd (%)',
    'Eff_rev (%)',
    'Hysteresis Index (%)',
    'Pmax_fwd',
    'Pmax_rev'
  ]];

  Object.keys(pairedMetrics).sort().forEach(sample => {
    const fwd = pairedMetrics[sample].fwd;
    const rev = pairedMetrics[sample].rev;
    if (!fwd || !rev) return;

    const hi = calculateHysteresisIndex_(fwd.efficiency, rev.efficiency);

    hysteresisRows.push([
      sample,
      fwd.efficiency,
      rev.efficiency,
      hi,
      fwd.pmaxDensity,
      rev.pmaxDensity
    ]);
  });

  summarySheet.getRange(startRow, 1, hysteresisRows.length, hysteresisRows[0].length).setValues(hysteresisRows);

  // Overlay chart using all pairs of columns
  if (overlayCol > 1) {
    const lastRow = overlaySheet.getLastRow();
    const lastCol = overlaySheet.getLastColumn();

    const overlayChart = overlaySheet.newChart()
      .setChartType(Charts.ChartType.LINE)
      .addRange(overlaySheet.getRange(1, 1, lastRow, lastCol))
      .setPosition(2, lastCol + 2, 0, 0)
      .setOption('title', 'All IV Curves Overlay')
      .setOption('legend', { position: 'right' })
      .setOption('hAxis', { title: 'Voltage' })
      .setOption('vAxis', { title: 'Current Density / Current' })
      .build();

    overlaySheet.insertChart(overlayChart);
  }

  // Basic formatting
  [overlaySheet, summarySheet].forEach(sh => {
    sh.getRange(1, 1, sh.getLastRow(), sh.getLastColumn()).setHorizontalAlignment('center');
    sh.autoResizeColumns(1, sh.getLastColumn());
  });
}


// -------------------- helpers --------------------

function makeValidSheetName_(name) {
  let cleaned = name.replace(/[\\\/\?\*\[\]\:]/g, '').trim();
  if (!cleaned) cleaned = 'CSV Import';
  return cleaned.substring(0, 100);
}

function findColumnIndex_(headers, possibleNames) {
  for (let i = 0; i < headers.length; i++) {
    const h = String(headers[i]).trim().toLowerCase();
    for (let j = 0; j < possibleNames.length; j++) {
      if (h === possibleNames[j].toLowerCase()) return i;
    }
  }
  return -1;
}

function safeNumber_(value) {
  const n = parseFloat(value);
  return isNaN(n) ? NaN : n;
}

function normalizeVoltage_(v) {
  // If the voltage looks like mV or scaled mV (like 20000), convert to volts
  if (Math.abs(v) > 10) return v / 1000;
  return v;
}

function interpolateZeroCrossing_(x1, y1, x2, y2) {
  if (y2 === y1) return x1;
  return x1 - y1 * (x2 - x1) / (y2 - y1);
}

function findVoc_(points) {
  for (let i = 0; i < points.length - 1; i++) {
    const y1 = points[i].j !== null ? points[i].j : points[i].current;
    const y2 = points[i + 1].j !== null ? points[i + 1].j : points[i + 1].current;
    if (isNaN(y1) || isNaN(y2)) continue;

    if ((y1 >= 0 && y2 <= 0) || (y1 <= 0 && y2 >= 0)) {
      return interpolateZeroCrossing_(points[i].v, y1, points[i + 1].v, y2);
    }
  }

  // fallback: closest to zero current density/current
  let best = points[0];
  let bestAbs = Infinity;
  points.forEach(p => {
    const y = p.j !== null ? p.j : p.current;
    if (y === null || isNaN(y)) return;
    if (Math.abs(y) < bestAbs) {
      bestAbs = Math.abs(y);
      best = p;
    }
  });
  return best.v;
}

function findJsc_(points) {
  let best = points[0];
  let bestAbs = Infinity;
  points.forEach(p => {
    if (Math.abs(p.v) < bestAbs) {
      bestAbs = Math.abs(p.v);
      best = p;
    }
  });
  return best.j !== null ? best.j : best.current;
}

function extractIvMetrics_(points) {
  let bestP = -Infinity;
  let vmpp = '';
  let jmpp = '';

  points.forEach(p => {
    const jVal = p.j !== null ? p.j : p.current;
    if (jVal === null || isNaN(jVal)) return;
    const pDensity = p.v * jVal; // if J is mA/cm² and V in volts, this is mW/cm²
    if (pDensity > bestP) {
      bestP = pDensity;
      vmpp = p.v;
      jmpp = jVal;
    }
  });

  const jsc = findJsc_(points);
  const voc = findVoc_(points);

  return {
    jsc: jsc,
    voc: voc,
    vmpp: vmpp,
    jmpp: jmpp,
    pmaxDensity: bestP,
    efficiency: bestP // under 100 mW/cm², efficiency(%) ≈ V * J if J is mA/cm²
  };
}

function calculateHysteresisIndex_(effFwd, effRev) {
  const maxEff = Math.max(Math.abs(effFwd), Math.abs(effRev));
  if (maxEff === 0) return 0;
  return Math.abs(effRev - effFwd) / maxEff * 100;
}
