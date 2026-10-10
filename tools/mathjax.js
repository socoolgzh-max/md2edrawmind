'use strict';
/**
 * MathJax v3 封装：TeX -> SVG（字形转路径，无外部字体依赖）。
 * 依赖：mathjax-full（npm install 已包含）。
 */
const { mathjax } = require('mathjax-full/js/mathjax.js');
const { TeX } = require('mathjax-full/js/input/tex.js');
const { SVG } = require('mathjax-full/js/output/svg.js');
const { liteAdaptor } = require('mathjax-full/js/adaptors/liteAdaptor.js');
const { RegisterHTMLHandler } = require('mathjax-full/js/handlers/html.js');
const { AllPackages } = require('mathjax-full/js/input/tex/AllPackages.js');

const adaptor = liteAdaptor({ fontSize: 16 });
RegisterHTMLHandler(adaptor);

const tex = new TeX({ packages: AllPackages, inlineMath: [['$', '$']] });
const svg = new SVG({ fontCache: 'local' });
const doc = mathjax.document('', { InputJax: tex, OutputJax: svg });

const cache = new Map();

/** 渲染一条 TeX，返回 { svg, widthEx, heightEx, error } */
function renderTex(texString, display = false) {
  const key = (display ? 'D:' : 'I:') + texString;
  if (cache.has(key)) return cache.get(key);
  let result;
  try {
    const node = doc.convert(String(texString || ''), { display, em: 16, ex: 8, containerWidth: 100000 });
    const svgText = adaptor.innerHTML(node);
    result = {
      svg: svgText,
      widthEx: parseFloat((svgText.match(/width="([\d.]+)ex"/) || [])[1] || '0'),
      heightEx: parseFloat((svgText.match(/height="([\d.]+)ex"/) || [])[1] || '0'),
      error: null
    };
  } catch (err) {
    result = { svg: null, widthEx: 0, heightEx: 0, error: String((err && err.message) || err) };
  }
  cache.set(key, result);
  return result;
}

/** ex -> px */
function exToPx(ex, fontSizePx = 16) {
  return (ex * fontSizePx) / 2;
}

/** SVG -> data URI（可直接塞进 <img src>） */
function toDataUri(svgText) {
  return 'data:image/svg+xml;base64,' + Buffer.from(svgText, 'utf8').toString('base64');
}

module.exports = { renderTex, exToPx, toDataUri };
