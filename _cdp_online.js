/* 线上验收（真实 Chrome）：打 CloudBase 静态托管域名，验证「打开即用 + 走的是后端」。

本地跑 vs 线上跑的差异，正是这份脚本存在的理由：
  · 本地同源，线上是静态域名 -> 网关域名，跨域是新增变量
  · 本地有 SQLite，线上靠 db_bootstrap 冷启自举，可能空库

判定标准定在页面底部那行 V2.0 文案（js/pages.js:104-105）：
    dataSource === 'api'  ->  "后端 API 数据源" + "207 味食材"
    否则                 ->  "本地副本（后端未连接）"
这比只看 /api/health 200 更接近用户实际看到的东西。

注意「 CloudBase 默认域名 first-visit 拦截」：
新 profile 首次访问会撞上官方「风险提醒」页（且返回 404 状态码），
必须先点「确定访问」，之后写 cookie 放行。这里第一步就处理掉它，
否则后面所有断言都会莫名其妙地 FAIL。正式解决要靠绑定已备案的自有域名。 */
const { spawn } = require('child_process');
const WebSocket = require('ws');
const http = require('http');
const os = require('os');
const path = require('path');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9347;
const APP = process.env.YS_WEB_URL ||
  'https://jieqi-yaoshan-d7gd6ypfscd10299f-1308818540.tcloudbaseapp.com/';
const API_HOST = 'jieqi-yaoshan-d7gd6ypfscd10299f-1308818540.ap-shanghai.app.tcloudbase.com';

const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJSON = p => new Promise((res, rej) => {
  http.get('http://127.0.0.1:' + PORT + p, r => {
    let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(JSON.parse(d)));
  }).on('error', rej);
});
const checks = [];
const ok = (n, c, e) => checks.push([n, !!c, e || '']);

(async () => {
  const profile = path.join(os.tmpdir(), 'cdp-ys-online-' + Date.now());
  const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--no-first-run',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + profile, 'about:blank'], { stdio: 'ignore' });
  let ver = null;
  for (let i = 0; i < 60 && !ver; i++) { await sleep(300); try { ver = await getJSON('/json/version'); } catch (e) { } }
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise(r => { ws.on('open', r); });

  let id = 0; const pending = {}; const consoleErrs = [];
  ws.on('message', m => {
    const msg = JSON.parse(m);
    if (msg.id && pending[msg.id]) { pending[msg.id](msg); delete pending[msg.id]; return; }
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails || {};
      consoleErrs.push((d.exception && d.exception.description) || d.text || 'unknown');
    }
    if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
      consoleErrs.push(msg.params.entry.text);
    }
  });
  const send = (method, params, sessionId) => {
    const i = ++id; const o = { id: i, method, params: params || {} };
    if (sessionId) o.sessionId = sessionId;
    ws.send(JSON.stringify(o));
    return new Promise(r => { pending[i] = r; });
  };

  const t = await send('Target.createTarget', { url: 'about:blank' });
  const att = await send('Target.attachToTarget', { targetId: t.result.targetId, flatten: true });
  const sid = att.result.sessionId;
  await send('Runtime.enable', {}, sid);
  await send('Log.enable', {}, sid);
  await send('Page.enable', {}, sid);

  const ev = async e => {
    const r = await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true }, sid);
    if (r.result && r.result.exceptionDetails) return 'ERR:' + ((r.result.exceptionDetails.exception || {}).description);
    return r.result && r.result.result ? r.result.result.value : undefined;
  };
  const bodyText = async () => ev("(document.body.innerText||'').replace(/\\s+/g,' ')");

  console.log('目标：' + APP);

  // ---------- 0) 越过 CloudBase 默认域名首访拦截 ----------
  // 时序是实测出来的，别乱改：navigate 后约 4s 拦截页才渲染完，
  // 点「确定访问」后真正的 index.html 才开始加载，__state 要到 +8~12s 才挂上。
  // 之前用 document.readyState 做同步，结果点击落在拦截页渲染完成之前，
  // 后面所有断言白等一轮全 FAIL —— 这里改成固定等待 + 轮询 __state。
  await send('Page.navigate', { url: APP }, sid);
  await sleep(4000);
  let blocked = false;
  if (await ev("/风险提醒|页面访问提示|确定访问/.test(document.title + document.body.innerText)") === true) {
    blocked = true;
    await ev("(function(){var b=[].slice.call(document.querySelectorAll('button')).filter(function(x){return /确定访问/.test(x.textContent)})[0]; if(b) b.click();})()");
    await sleep(4000);
  }
  await sleep(8000);

  // ---------- 1) Vue 挂载 ----------
  let ready = false;
  for (let i = 0; i < 45; i++) {
    if (await ev('!!(window.__state && window.__state.role)') === true) { ready = true; break; }
    await sleep(1000);
  }
  ok('页面加载并完成 Vue 挂载', ready, blocked ? '首访被官方风险提醒页拦截，已放行' : '');
  await sleep(3000); // 等列表数据与 apiBase 探测落定

  // ---------- 2) 是否连上后端 ----------
  const foot = String(await bodyText());
  ok('底部标注走后端 API 数据源', /后端 API 数据源/.test(foot), /本地副本（后端未连接）/.test(foot) ? '实际是本地副本！' : '');
  const mIng = foot.match(/(\d+)\s*味食材/);
  const ingCount = mIng ? parseInt(mIng[1], 10) : null;
  ok('食材 207 味（云端完整数据）', ingCount === 207, '实际 ' + ingCount);
  const mDis = foot.match(/(\d+)\s*道膳方/);
  ok('膳方 154 道（云端完整数据）', mDis && parseInt(mDis[1], 10) === 154, mDis ? mDis[0] : '未读到');

  const usedBase = await ev('(window.YS_API_BASE || (window.YS_CLOUD_CONFIG && window.YS_CLOUD_CONFIG.apiBase) || "")');
  const baseStr = Array.isArray(usedBase) ? usedBase.join(',') : String(usedBase);
  ok('apiBase 指向网关域名', baseStr.indexOf(API_HOST) >= 0, String(baseStr).slice(0, 80));

  // ---------- 3) 控制台干净 ----------
  const realErrs = consoleErrs.filter(e => !/favicon|云开发未配置|Failed to load resource/i.test(e));
  ok('控制台无 JS 异常', realErrs.length === 0, realErrs.slice(0, 2).join(' | ').slice(0, 220));

  // ---------- 4) 三场景真的能生成 ----------
  await ev("window.__state.roleKey='B'; window.__state.role.set('B'); window.__state.showRolePicker=false; window.__state.page='gen'; 'ok'");
  await sleep(1800);
  ok('能进入生成页', /用餐场景|生成/.test(String(await bodyText())), '');

  const genNow = async () => {
    await ev("(function(){var b=[].slice.call(document.querySelectorAll('button')).filter(function(x){return /生成/.test(x.textContent)})[0]; if(b) b.click();})()");
    for (let i = 0; i < 50; i++) {
      await sleep(500);
      if (await ev("window.__state.genView==='result' && !!window.__state.banquet") === true) break;
    }
    await sleep(900);
    return bodyText();
  };

  await ev("window.__state.form.type='health'; window.__state.form.finale='dessert'; window.__state.form.headcount=10; window.__state.genView='form'; 'ok'");
  await sleep(1000);
  const hea = String(await genNow());
  ok('养生宴线上生成 17 道', /共 17 道/.test(hea), (hea.match(/共 \d+ 道/) || [''])[0]);
  ok('养生宴冷菜 6 道', /迎宾冷菜（6道）/.test(hea), '');
  ok('养生宴写明 10 人席', /按 10 人席设计/.test(hea), '');

  await ev("window.__state.genView='form'; window.__state.form.type='family'; 'ok'");
  await sleep(1000);
  const fam = String(await genNow());
  ok('家庭餐线上生成 6 道', /共 6 道/.test(fam), (fam.match(/共 \d+ 道/) || [''])[0]);

  await ev("window.__state.genView='form'; window.__state.form.type='business'; 'ok'");
  await sleep(1000);
  const bus = String(await genNow());
  ok('商务宴线上生成 8 道', /共 8 道/.test(bus), (bus.match(/共 \d+ 道/) || [''])[0]);

  ok('三场景均未出现生成失败', !/生成失败|Failed to fetch|网络错误/.test(hea + fam + bus), '');

  console.log('\n=== 线上真实浏览器验收 ===');
  let pass = 0;
  checks.forEach(c => {
    if (c[1]) pass++;
    console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] ? '  [' + c[2] + ']' : ''));
  });
  console.log('\n' + pass + '/' + checks.length + ' 通过');
  chrome.kill(); ws.close();
  process.exit(pass === checks.length ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
