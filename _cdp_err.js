/* 真实 Chrome 验证��后端挂掉时的错误卡片，以及「检测后端」能否自愈 */
const { spawn } = require('child_process');
const WebSocket = require('ws');
const http = require('http');
const os = require('os');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9337;
const APP = 'http://127.0.0.1:8000/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJSON = p => new Promise((res, rej) => {
  http.get('http://127.0.0.1:' + PORT + p, r => { let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(JSON.parse(d))); }).on('error', rej);
});

const checks = [];
const ok = (n, c, e) => checks.push([n, !!c, e]);

(async () => {
  const profile = path.join(os.tmpdir(), 'cdp-ys-err-' + Date.now());
  const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--no-first-run',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + profile, 'about:blank'], { stdio: 'ignore' });
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) { await sleep(300); try { ver = await getJSON('/json/version'); } catch (e) {} }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.on('open', r); ws.on('error', j); });
  let id = 0; const pending = {};
  ws.on('message', m => {
    const msg = JSON.parse(m);
    if (msg.id && pending[msg.id]) { pending[msg.id](msg); delete pending[msg.id]; }
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

  ok('页面已挂载', await ev('!!window.__state'));
  await ev("window.__state.roleKey='A'; window.__state.showRolePicker=false; window.__state.page='gen'; window.__state.genView='form'; 'ok'");
  await sleep(800);

  /* --- 1. 掐断后端：只让后续请求失败 --- */
  await ev("window.__realFetch = window.fetch.bind(window); window.fetch = function(){ return Promise.reject(new TypeError('Failed to fetch')); }; 'ok'");
  const btnClicked = await ev(`(function(){
    var b=[].slice.call(document.querySelectorAll('button')).filter(function(x){return /生成/.test(x.textContent) && x.className.indexOf('primary')>=0;})[0];
    if(!b) return 'no-btn'; b.click(); return 'clicked';
  })()`);
  ok('找到并点击生成按钮', btnClicked === 'clicked', btnClicked);
  await sleep(2500);

  const errTitle = await ev("(document.querySelector('.err-title')||{}).textContent || ''");
  const errWhy = await ev("(document.querySelector('.err-why')||{}).textContent || ''");
  const steps = await ev("(function(){var n=document.querySelectorAll('.err-steps li');return [].map.call(n,function(x){return x.textContent;}).join(' | ')})()");
  ok('错误卡片出现', /连不上后端/.test(errTitle), errTitle);
  ok('说明不出未校验结果', /不产出未校验结果/.test(errWhy || ''));
  ok('步骤指向启动脚本', /启动节气药膳师/.test(steps || ''), (steps || '').slice(0, 90));
  ok('步骤给出访问地址', /127\.0\.0\.1:8000/.test(steps || ''));
  ok('未产出结果页', (await ev('window.__state.genView')) === 'form');
  const hasRetry = await ev("[].slice.call(document.querySelectorAll('button')).some(function(b){return b.textContent.indexOf('重试')>=0})");
  const hasRecheck = await ev("[].slice.call(document.querySelectorAll('button')).some(function(b){return b.textContent.indexOf('检测后端')>=0})");
  ok('有「重试」按钮', hasRetry);
  ok('有「检测后端」按钮', hasRecheck);

  /* --- 2. 恢复后端，点「检测后端」应当自愈并直接出结果 --- */
  await ev("window.fetch = window.__realFetch; 'ok'");
  console.log('  [诊断] 恢复后 diagnose:', await ev("(async()=>JSON.stringify(await window.API.diagnose()))()"));
  await ev("(function(){var b=[].slice.call(document.querySelectorAll('button')).filter(function(x){return x.textContent.indexOf('检测后端')>=0;})[0]; if(b) b.click(); return 'ok'})()");
  await sleep(4000);
  console.log('  [诊断] loading:', await ev('window.__state.loading'),
    '| genError:', await ev('window.__state.genError'),
    '| errBox:', await ev("(window.__state.errBox||{}).title||'无'"),
    '| checking:', await ev('window.__state.checking'));
  ok('点检测后端后自动恢复并出结果', (await ev('window.__state.genView')) === 'result', await ev('window.__state.genView'));
  ok('结果有菜品', (await ev('(window.__state.banquet||{dishes:[]}).dishes.length')) > 0,
    await ev('(window.__state.banquet||{dishes:[]}).dishes.length'));
  ok('错误卡片已消失', !(await ev("!!document.querySelector('.err-box')")));

  console.log('\n=== 真实 Chrome：生成失败与自愈 ===');
  let pass = 0;
  checks.forEach(c => { if (c[1]) pass++; console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] !== undefined ? '  [' + c[2] + ']' : '')); });
  console.log('\n' + pass + '/' + checks.length + ' 通过');
  chrome.kill();
  ws.close();
  process.exit(pass === checks.length ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
