/* 逐个角色 + 不同入口，在真实 Chrome 里测食材库搜索 */
const { spawn } = require('child_process');
const WebSocket = require('ws');
const http = require('http');
const os = require('os');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9335;
const APP = 'http://127.0.0.1:8000/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJSON = p => new Promise((res, rej) => {
  http.get('http://127.0.0.1:' + PORT + p, r => { let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(JSON.parse(d))); }).on('error', rej);
});

(async () => {
  const profile = path.join(os.tmpdir(), 'cdp-ys-roles-' + Date.now());
  const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--no-first-run',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + profile, 'about:blank'], { stdio: 'ignore' });
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) { await sleep(300); try { ver = await getJSON('/json/version'); } catch (e) {} }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.on('open', r); ws.on('error', j); });
  let id = 0; const pending = {}; const errs = [];
  ws.on('message', m => {
    const msg = JSON.parse(m);
    if (msg.id && pending[msg.id]) { pending[msg.id](msg); delete pending[msg.id]; return; }
    if (msg.method === 'Runtime.exceptionThrown')
      errs.push((msg.params.exceptionDetails.exception && msg.params.exceptionDetails.exception.description || msg.params.exceptionDetails.text || '').split('\n')[0]);
  });
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

  const rows = () => ev("document.querySelectorAll('.el-table__body tbody tr').length");

  for (const role of ['A', 'B', 'C']) {
    await ev("window.__state.roleKey='" + role + "'; window.__state.showRolePicker=false; window.__state.kw=''; window.__state.page='ing'; 'ok'");
    await sleep(1200);
    const total = await rows();
    await ev("document.querySelector('.el-input__inner').focus(); 'ok'");
    await send('Input.insertText', { text: '山药' }, sid);
    await sleep(800);
    const r1 = await rows(); const kw1 = await ev('window.__state.kw');
    await ev("window.__state.kw=''; 'ok'"); await sleep(400);
    await ev("document.querySelector('.el-input__inner').focus(); 'ok'");
    await send('Input.insertText', { text: '黄芪' }, sid);
    await sleep(800);
    const r2 = await rows(); const kw2 = await ev('window.__state.kw');
    console.log(`角色 ${role}: 总${total}行 | 搜山药 kw=${JSON.stringify(kw1)} → ${r1}行 | 搜黄芪 kw=${JSON.stringify(kw2)} → ${r2}行`);
  }

  // 模拟真实点击：从首页点「食材库」卡片进去再搜
  await ev("window.__state.roleKey='B'; window.__state.page='home'; window.__state.kw=''; 'ok'");
  await sleep(900);
  const clicked = await ev(`(function(){
    var cards=[].slice.call(document.querySelectorAll('.btn-card'));
    var c=cards.filter(function(x){return x.textContent.indexOf('食材')>=0 || x.textContent.indexOf('食材库')>=0;})[0];
    if(!c) return 'no-card';
    c.click(); return 'clicked';
  })()`);
  await sleep(1200);
  console.log('从首页点卡片进入:', clicked, '| 当前页:', await ev('window.__state.page'));
  console.log('表格行数:', await rows());
  await ev("document.querySelector('.el-input__inner').focus(); 'ok'");
  await send('Input.insertText', { text: '山药' }, sid);
  await sleep(900);
  console.log('点进去后搜山药 →', await rows(), '行, kw =', JSON.stringify(await ev('window.__state.kw')));
  console.log('计数行:', await ev("(document.querySelector('.ing-count')||{}).textContent"));

  console.log('异常:', errs.length ? errs.slice(0, 5).join(' | ') : '无');
  ws.close(); chrome.kill();
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
