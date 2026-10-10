'use strict';

const $ = (id) => document.getElementById(id);
const drop = $('drop');
const fileInput = $('file');

/* ---------------- 环境探测 ---------------- */
fetch('/api/env').then((r) => r.json()).then((env) => {
  const badge = $('envBadge');
  const missing = [];
  if (!env.node) missing.push('Node.js');
  if (!env.chrome) missing.push('Chrome');
  if (missing.length) {
    badge.textContent = '缺少 ' + missing.join(' / ');
    badge.className = 'badge bad';
    badge.title = '公式渲染需要 Node.js 与 Chrome/Edge';
  } else {
    badge.textContent = '环境就绪 ✔';
    badge.className = 'badge ok';
  }
}).catch(() => {});

/* ---------------- 选择文件 ---------------- */
$('pick').addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
drop.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) start(fileInput.files[0]);
});

['dragenter', 'dragover'].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', (e) => {
  const f = e.dataTransfer.files && e.dataTransfer.files[0];
  if (f) start(f);
});

/* ---------------- 上传并跟踪进度 ---------------- */
let currentJob = null;

function start(file) {
  const panel = $('panel');
  panel.classList.remove('hidden');
  $('barFill').style.width = '0%';
  $('pct').textContent = '0%';
  $('msg').textContent = '上传中…';
  $('stats').textContent = '';
  $('files').innerHTML = '';
  $('log').textContent = '';
  const old = panel.querySelector('.err');
  if (old) old.remove();

  const fd = new FormData();
  fd.append('file', file, file.name);
  fd.append('mix', $('mix').value);
  fd.append('limit', $('limit').value || '0');
  fd.append('outline', $('outline').checked ? '1' : '0');

  fetch('/api/upload', { method: 'POST', body: fd })
    .then((r) => r.json())
    .then((res) => {
      if (res.error) throw new Error(res.error);
      currentJob = res.job;
      $('msg').textContent = '开始转换 ' + (res.name || '');
      follow(res.job);
    })
    .catch((err) => fail(err.message));
}

function follow(jobId) {
  const es = new EventSource('/api/progress/' + jobId);
  es.onmessage = (ev) => {
    let data;
    try { data = JSON.parse(ev.data); } catch { return; }
    const pct = data.pct || 0;
    $('barFill').style.width = pct + '%';
    $('pct').textContent = pct + '%';
    if (data.message) $('msg').textContent = data.message;
    if (data.log && data.log.length) {
      const log = $('log');
      log.textContent = data.log.join('\n');
      log.scrollTop = log.scrollHeight;
    }
    if (data.status === 'done') {
      $('stats').textContent =
        `主题 ${data.nodes} 个 · 公式 ${data.formulas} 条` +
        (data.missing ? ` · ⚠ ${data.missing} 条未渲染` : '');
      renderFiles(data.files || []);
    }
    if (data.status === 'error') fail(data.error || '转换失败');
  };
  es.addEventListener('end', () => es.close());
  es.onerror = () => es.close();
}

function renderFiles(files) {
  const ul = $('files');
  ul.innerHTML = '';
  files.forEach((f, i) => {
    const li = document.createElement('li');
    const kb = Math.max(1, Math.round(f.size / 1024));
    li.innerHTML = `<b>${f.name}</b><span class="size">${kb} KB</span>
      <a href="/api/download/${currentJob}/${i}">下载</a>`;
    ul.appendChild(li);
  });
  $('msg').textContent = '完成 —— 下一步：EdrawMind → 导入 → Word';
}

function fail(msg) {
  const panel = $('panel');
  const div = document.createElement('div');
  div.className = 'err';
  div.textContent = '✗ ' + msg;
  panel.appendChild(div);
  $('msg').textContent = '出错了';
  $('barFill').style.width = '100%';
  $('barFill').style.background = 'linear-gradient(90deg,#f87171,#dc2626)';
}
