/* 真实 Chrome 验证：食材库扩充到 195 味 / 目录内 106 种，搜索与目录归属列是否正常 */
const { spawn } = require('child_process');
const WebSocket = require('ws');
const http = require('http');
const os = require('os');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9339;
const APP = 'http://127.0.0.1:8000/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJSON = p => new Promise((res, rej) => {
  http.get('http://127.0.0.1:' + PORT + p, r => { let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(JSON.parse(d))); }).on('error', rej);
});
const checks = [];
const ok = (n, c, e) => checks.push([n, !!c, e]);

(async () => {
  const profile = path.join(os.tmpdir(), 'cdp-ys-cat-' + Date.now());
  const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--no-first-run',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + profile, 'about:blank'], { stdio: 'ignore' });
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) { await sleep(300); try { ver = await getJSON('/json/version'); } catch (e) {} }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.on('open', r); ws.on('error', j); });
  let id = 0; const pending = {};
  ws.on('message', m => { const msg = JSON.parse(m); if (msg.id && pending[msg.id]) { pending[msg.id](msg); delete pending[msg.id]; } });
  const send = (method, params, sessionId) => {
    const i = ++id; const o = { id: i, method, params: params || {} };
    if (sessionId) o.sessionId = sessionId;
    ws.send(JSON.stringify(o));
    return new Promise(r => { pending[i] = r; });
  };
  const t = await send('Target.createTarget', { url: APP });
  const att = await send('Target.attachToTarget', { targetId: t.result.targetId, flatten: true });
  const sid = att.result.sessionId;
  await send('Runtime.enable', {}, sid);
  const ev = async e => {
    const r = await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true }, sid);
    if (r.result && r.result.exceptionDetails) return 'ERR:' + (r.result.exceptionDetails.exception || {}).description;
    return r.result && r.result.result ? r.result.result.value : undefined;
  };
  for (let i = 0; i < 40; i++) { if (await ev('!!window.__state')) break; await sleep(500); }

  await ev("window.__state.roleKey='A'; window.__state.showRolePicker=false; window.__state.kw=''; window.__state.ingKind='all'; window.__state.ingCat=''; window.__state.page='ing'; 'ok'");
  await sleep(1500);

  const rows = () => ev("document.querySelectorAll('.el-table__body tbody tr').length");
  ok('食材总数 195', (await ev('window.__state.ingredients.length')) === 195, await ev('window.__state.ingredients.length'));
  ok('目录内 106', (await ev("window.__state.ingredients.filter(i=>i.in_catalog===1).length")) === 106,
    await ev("window.__state.ingredients.filter(i=>i.in_catalog===1).length"));
  ok('底部显示目录内计数', /目录内 106 种/.test(await ev("document.body.textContent")), '');

  const search = async kw => {
    await ev("window.__state.kw='" + kw + "'; 'ok'");
    await sleep(700);
    return rows();
  };
  ok('搜「化橘红」有结果', (await search('化橘红')) === 1, await search('化橘红'));
  ok('搜官方名「龙眼肉」能命中桂圆', (await search('龙眼肉')) >= 1, await search('龙眼肉'));
  ok('搜「山药」有结果', (await search('山药')) >= 1, await search('山药'));
  await ev("window.__state.kw=''; 'ok'"); await sleep(500);

  // 目录归属列
  await ev("window.__state.ingKind='catalog'; 'ok'"); await sleep(800);
  ok('药食同源筛选 106 行', (await rows()) === 106, await rows());
  const tag = await ev("(function(){var t=[].map.call(document.querySelectorAll('.cat-yes'),function(x){return x.textContent.trim()});return t.slice(0,3).join(' / ')})()");
  ok('目录归属列显示批次', /药食同源 · \d{4}/.test(tag || ''), tag);
  await ev("window.__state.ingKind='food'; 'ok'"); await sleep(800);
  ok('普通食品筛选 89 行', (await rows()) === 89, await rows());

  console.log('\n=== 真实 Chrome：食材库扩充 ===');
  let pass = 0;
  checks.forEach(c => { if (c[1]) pass++; console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] !== undefined ? '  [' + c[2] + ']' : '')); });
  console.log('\n' + pass + '/' + checks.length + ' 通过');
  chrome.kill(); ws.close();
  process.exit(pass === checks.length ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
