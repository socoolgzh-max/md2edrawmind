#!/usr/bin/env node
'use strict';
/**
 * md2edrawmind · 公式渲染器（Node 侧）
 *
 * 把 formulas.txt 里的每条 LaTeX 渲染成图片：
 *   1) 用 MathJax 生成 SVG
 *   2) 排成一张精确坐标的"公式表" HTML
 *   3) 由浏览器无头截图
 *   4) 按坐标切成一张张 PNG
 *
 * 用法：
 *   node tools/render.js sheet <workDir>         生成 sheet.html + sheet.json，并打印高度
 *   node tools/render.js slice <workDir>         按 sheet.json 切图 → formula-png/ + formula-pngs.json
 *   node tools/render.js tex2svg <workDir>       仅生成矢量 SVG（formula-svg/），不需要浏览器
 */
const fs = require('fs');
const path = require('path');

const { renderTex, exToPx } = require('./mathjax.js');

const FONT = 16;   // px；与 build_docx.py 的换算基准一致（1pt = 1/72in）
const PAD_X = 6;
const PAD_Y = 5;

function readFormulas(workDir) {
  const p = path.join(workDir, 'formulas.txt');
  if (!fs.existsSync(p)) throw new Error('缺少 formulas.txt：请先用 md2edrawmind 解析 Markdown');
  return fs
    .readFileSync(p, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((l) => l.split('\t')[1])
    .filter(Boolean);
}

/** 生成公式表 HTML + 坐标清单 */
function buildSheet(workDir) {
  const formulas = readFormulas(workDir);
  const rows = [];
  let y = 0;
  let maxW = 0;
  const EX = FONT / 2;

  formulas.forEach((tex, idx) => {
    const r = renderTex(tex, false);
    const head = (r.svg || '').slice(0, 400);
    const vb = head.match(/viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"/);
    const vbW = vb ? parseFloat(vb[3]) : 0;
    const vbH = vb ? parseFloat(vb[4]) : 0;
    const dispW = (r.widthEx || 1) * EX;
    const dispH = (r.heightEx || 1) * EX;

    // 高度按 display 尺寸留 10% 余量（分式/求和的下沿），宽度按 viewBox 纵横比反推
    let realH = dispH * 1.1;
    let realW = realH * (vbW > 0 && vbH > 0 ? vbW / vbH : 1);
    if (vbW > 0 && vbH > 0 && realW < dispW * 0.9) realW = dispW * 0.9;

    const w = r.svg ? Math.ceil(realW) : 140;
    const h = r.svg ? Math.ceil(realH) : 22;
    const rowH = h + PAD_Y * 2;
    const svg = (r.svg || '').replace(/^<svg style="[^"]*"/, '<svg style="display:block"');

    rows.push({
      i: idx + 1,
      tex,
      rowX: 0,
      rowY: y,
      rowW: w + PAD_X * 2,
      rowH,
      boxX: PAD_X,
      boxY: PAD_Y,
      boxW: w,
      boxH: h,
      svg
    });
    y += rowH;
    maxW = Math.max(maxW, w + PAD_X * 2);
  });

  const width = Math.max(240, maxW);
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"/><style>
 html,body{margin:0;padding:0;background:#fff}
 .row{position:relative;overflow:hidden}
 .row svg{position:absolute}
</style></head><body>
${rows
  .map(
    (r) =>
      `<div class="row" style="width:${width}px;height:${r.rowH}px">` +
      (r.svg
        ? r.svg.replace(/^<svg /, `<svg style="left:${r.boxX}px;top:${r.boxY}px;" `)
        : `<span style="position:absolute;left:${r.boxX}px;top:${r.boxY}px;font:14px sans-serif">${r.tex}</span>`) +
      '</div>'
  )
  .join('\n')}
</body></html>`;

  fs.mkdirSync(workDir, { recursive: true });
  fs.writeFileSync(path.join(workDir, 'sheet.html'), html, 'utf8');
  fs.writeFileSync(
    path.join(workDir, 'sheet.json'),
    JSON.stringify({ width, height: y, padding: { x: PAD_X, y: PAD_Y }, rows: rows.map(({ svg, ...r }) => r) }, null, 1),
    'utf8'
  );
  return { count: rows.length, width, height: y };
}

/** 裁切：整数坐标 + 去白边 */
function sliceSheet(workDir) {
  const { PNG } = require('pngjs');
  const sheetPath = path.join(workDir, 'sheet.png');
  const metaPath = path.join(workDir, 'sheet.json');
  if (!fs.existsSync(sheetPath)) throw new Error('缺少 sheet.png：浏览器截图失败');
  const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
  const sheet = PNG.sync.read(fs.readFileSync(sheetPath));
  const dest = path.join(workDir, 'formula-png');
  fs.mkdirSync(dest, { recursive: true });

  const crop = (x0, y0, w, h) => {
    x0 = Math.max(0, Math.min(sheet.width - 1, Math.round(x0)));
    y0 = Math.max(0, Math.min(sheet.height - 1, Math.round(y0)));
    w = Math.max(1, Math.min(sheet.width - x0, Math.round(w)));
    h = Math.max(1, Math.min(sheet.height - y0, Math.round(h)));
    const out = new PNG({ width: w, height: h });
    let minX = w, minY = h, maxX = -1, maxY = -1;
    for (let yy = 0; yy < h; yy++) {
      for (let xx = 0; xx < w; xx++) {
        const si = ((y0 + yy) * sheet.width + (x0 + xx)) << 2;
        const di = (yy * w + xx) << 2;
        const r = sheet.data[si], g = sheet.data[si + 1], b = sheet.data[si + 2];
        out.data[di] = r; out.data[di + 1] = g; out.data[di + 2] = b; out.data[di + 3] = 255;
        if (r < 245 || g < 245 || b < 245) {
          if (xx < minX) minX = xx;
          if (yy < minY) minY = yy;
          if (xx > maxX) maxX = xx;
          if (yy > maxY) maxY = yy;
        }
      }
    }
    if (maxX < 0) return out;                    // 整块空白（渲染失败）
    const pad = 2;
    minX = Math.max(0, minX - pad); minY = Math.max(0, minY - pad);
    maxX = Math.min(w - 1, maxX + pad); maxY = Math.min(h - 1, maxY + pad);
    const cw = maxX - minX + 1, ch = maxY - minY + 1;
    const c = new PNG({ width: cw, height: ch });
    for (let yy = 0; yy < ch; yy++) {
      for (let xx = 0; xx < cw; xx++) {
        const si = ((minY + yy) * w + (minX + xx)) << 2;
        const di = (yy * cw + xx) << 2;
        c.data[di] = out.data[si]; c.data[di + 1] = out.data[si + 1];
        c.data[di + 2] = out.data[si + 2]; c.data[di + 3] = 255;
      }
    }
    return c;
  };

  const manifest = meta.rows.map((row) => {
    const img = crop(row.rowX + row.boxX, row.rowY + row.boxY, row.boxW, row.boxH);
    const name = 'f' + String(row.i).padStart(3, '0') + '.png';
    const file = path.join(dest, name);
    fs.writeFileSync(file, PNG.sync.write(img));
    return { index: row.i, tex: row.tex, file, width: img.width, height: img.height };
  });

  fs.writeFileSync(path.join(workDir, 'formula-pngs.json'), JSON.stringify(manifest, null, 1), 'utf8');
  return { count: manifest.length, dest };
}

/** 只出矢量图（不需要浏览器，质量最高，供手动拖拽使用） */
function texToSvg(workDir) {
  const formulas = readFormulas(workDir);
  const dest = path.join(workDir, 'formula-svg');
  fs.mkdirSync(dest, { recursive: true });
  let ok = 0;
  formulas.forEach((tex, idx) => {
    const r = renderTex(tex, false);
    if (r.svg) {
      fs.writeFileSync(path.join(dest, 'f' + String(idx + 1).padStart(3, '0') + '.svg'), r.svg, 'utf8');
      ok++;
    }
  });
  return { count: ok, dest };
}

function main() {
  const cmd = process.argv[2];
  const workDir = process.argv[3] || 'work';
  try {
    let out;
    if (cmd === 'sheet') out = buildSheet(workDir);
    else if (cmd === 'slice') out = sliceSheet(workDir);
    else if (cmd === 'tex2svg') out = texToSvg(workDir);
    else {
      console.error('usage: node tools/render.js <sheet|slice|tex2svg> <workDir>');
      process.exit(2);
    }
    console.log(JSON.stringify(out));
  } catch (err) {
    console.error('[render] ' + (err && err.message ? err.message : err));
    process.exit(1);
  }
}

if (require.main === module) main();
module.exports = { buildSheet, sliceSheet, texToSvg };
