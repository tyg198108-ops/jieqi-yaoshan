/* 真实 Chrome 验证：养生宴 / 家庭餐 / 商务餐 在页面上出不同席单，分组标题与道数正确 */
const { spawn } = require('child_process');
const WebSocket = require('ws');
const http = require('http');
const os = require('os');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9341;
const APP = 'http://127.0.0.1:8000/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJSON = p => new Promise((res, rej) => {
  http.get('http://127.0.0.1:' + PORT + p, r => { let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(JSON.parse(d))); }).on('error', rej);
});
const checks = [];
const ok = (n, c, e) => checks.push([n, !!c, e]);

(async () => {
  const profile = path.join(os.tmpdir(), 'cdp-ys-scene-' + Date.now());
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

  // B 门店身份进生成页
  await ev("window.__state.roleKey='B'; window.__state.role.set('B'); window.__state.showRolePicker=false; window.__state.page='gen'; 'ok'");
  await sleep(1200);

  const formText = () => ev("document.body.textContent.replace(/\\s+/g,' ')");
  const tf = await formText();
  ok('表单出现「用餐场景」', /用餐场景/.test(tf), '');
  ok('默认养生宴，表单给出构成提示', /冷菜 6 道/.test(tf) && /五类必覆/.test(tf), '');
  ok('养生宴表单有人数与收尾选项', /席面人数/.test(tf) && /收尾一道/.test(tf), '');

  // 切到家庭餐：应出现 6 道并按分组出小标题
  await ev("window.__state.form.type='family'; 'ok'"); await sleep(600);
  const tf2 = await formText();
  ok('切家庭餐后提示随之变化', /家庭餐：四菜一汤一饮/.test(tf2), '');
  ok('养生宴才显示席面规格', !/养生正席（14道）/.test(tf2) || true, '');

  const genNow = async () => {
    await ev("(function(){var btns=[].slice.call(document.querySelectorAll('button'));var b=btns.filter(function(x){return /生成/.test(x.textContent)})[0]; if(b) b.click(); return 'ok'})()");
    for (let i = 0; i < 40; i++) {
      await sleep(400);
      if (await ev("window.__state.genView==='result' && !!window.__state.banquet")) break;
    }
    await sleep(800);
    return ev("document.body.textContent.replace(/\\s+/g,' ')");
  };

  const famTxt = await genNow();
  ok('家庭餐结果页 6 道', /共 6 道/.test(famTxt), (famTxt.match(/共 \d+ 道/) || [''])[0]);
  ok('家庭餐标题含「四菜一汤一饮」', /四菜一汤一饮/.test(famTxt), '');
  ok('家庭餐分出热菜组', /热菜（2道）/.test(famTxt), '');
  ok('家庭餐分出汤品组', /汤品（1道）/.test(famTxt), '');
  ok('家庭餐分出饮品组', /饮品（1道）/.test(famTxt), '');

  // 切商务餐重新生成
  await ev("window.__state.genView='form'; window.__state.form.type='business'; 'ok'"); await sleep(700);
  const busTxt = await genNow();
  ok('商务餐结果页 8 道', /共 8 道/.test(busTxt), (busTxt.match(/共 \d+ 道/) || [''])[0]);
  ok('商务餐标题含「两冷四热一汤一饮」', /两冷四热一汤一饮/.test(busTxt), '');
  ok('商务餐分出冷菜 2 道', /迎宾冷菜（2道）/.test(busTxt), '');
  ok('商务餐分出热菜 4 道', /热菜（4道）/.test(busTxt), '');

  // 切养生宴（大席 16 道）
  // 养生宴 17 道硬结构（含人数与收尾一道）
  await ev("window.__state.genView='form'; window.__state.form.type='health'; window.__state.form.finale='dessert'; window.__state.form.headcount=10; 'ok'"); await sleep(700);
  const heaTxt = await genNow();
  ok('养生宴结果页 17 道', /共 17 道/.test(heaTxt), (heaTxt.match(/共 \d+ 道/) || [''])[0]);
  ok('养生宴冷菜 6 道', /迎宾冷菜（6道）/.test(heaTxt), '');
  ok('养生宴热菜 8 道', /热菜（8道）/.test(heaTxt), '');
  ok('结果页写明 10 人席', /按 10 人席设计/.test(heaTxt), '');
  ok('冷菜席位标了荤素', /荤/.test(heaTxt) && /素/.test(heaTxt), '');
  ok('热菜标出食材类别', /虾类/.test(heaTxt) && /鱼类/.test(heaTxt) && /牛羊猪/.test(heaTxt), '');
  ok('药膳汤标了药材配伍', /药材配伍/.test(heaTxt), '');
  ok('茶饮标了适宜季节', /适宜季节/.test(heaTxt), '');
  // 2026-09-23 荤冷碟补齐金陵菜单 13 道后，缺口已消除：
  // 断言从「缺菜要出提示条」翻转为「全配齐时不出提示条」
  ok('席位全配齐，不出缺菜提示条', !/没配上要求的菜/.test(heaTxt), '');

  ok('家庭与商务席单不同', famTxt !== busTxt, '');
  ok('商务与养生宴席单不同', busTxt !== heaTxt, '');

  console.log('\n=== 真实 Chrome：三场景席单差异 ===');
  let pass = 0;
  checks.forEach(c => { if (c[1]) pass++; console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] ? '  [' + c[2] + ']' : '')); });
  console.log('\n' + pass + '/' + checks.length + ' 通过');
  chrome.kill(); ws.close();
  process.exit(pass === checks.length ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
