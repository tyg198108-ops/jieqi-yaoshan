/* 导航专项测试：结果页 ↔ 生成页 的一次点击返回、条件保留、浏览器前进/后退。
   用 jsdom 真实加载页面并真实点击 DOM 按钮。后端需先启动在 127.0.0.1:8000。 */
const { JSDOM, VirtualConsole } = require('jsdom');
const http = require('http');

const BASE = 'http://127.0.0.1:8000';
const sleep = ms => new Promise(r => setTimeout(r, ms));

function fetchPage(path) {
  return new Promise((resolve, reject) => {
    http.get(BASE + path, res => {
      let d = '';
      res.on('data', c => (d += c));
      res.on('end', () => resolve(d));
    }).on('error', reject);
  });
}

const checks = [];
const ok = (name, cond, extra) => checks.push([name, !!cond, extra || '']);

(async () => {
  const html = await fetchPage('/');
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push('jsdomError: ' + e.message));
  vc.on('error', (...a) => errors.push('console.error: ' + a.join(' ')));

  const dom = new JSDOM(html, {
    url: BASE + '/',
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      // jsdom 没有 fetch / print：补最小 shim
      window.fetch = (url, opts) =>
        globalThis.fetch(new URL(url, BASE).href, opts).then(r =>
          r.text().then(t => ({
            ok: r.ok, status: r.status,
            json: () => Promise.resolve(JSON.parse(t)),
            text: () => Promise.resolve(t)
          }))
        );
      window.print = () => {};
    }
  });
  const win = dom.window;
  const doc = win.document;

  // 等待 boot 完成
  for (let i = 0; i < 60 && !win.__state; i++) await sleep(200);
  if (!win.__state) { console.error('应用未启动'); process.exit(1); }
  const st = win.__state;

  // 选定角色，进入生成页
  st.roleKey = 'A'; st.showRolePicker = false;
  st.page = 'gen'; st.genView = 'form';
  st.form.tid = 16; st.form.cid = 2; st.form.group = 'none'; st.form.type = 'family';
  st.form.chronic = ['高血压'];
  await sleep(600);

  const before = JSON.parse(JSON.stringify(st.form));
  ok('进入生成页显示表单', doc.body.innerHTML.indexOf('选择节气') >= 0);

  // 找到生成按钮并真实点击
  const btn = [...doc.querySelectorAll('button')].find(b =>
    (b.textContent || '').indexOf('生成') >= 0 && (b.textContent || '').indexOf('返回') < 0);
  ok('生成页有生成按钮', !!btn, btn && btn.textContent.trim());
  btn.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));

  for (let i = 0; i < 60 && !st.banquet; i++) await sleep(200);
  ok('生成成功拿到结果', !!st.banquet);
  ok('生成后切到结果视图', st.genView === 'result', st.genView);
  await sleep(500);

  // 1. 结果页顶部有返回入口
  const bar = doc.querySelector('.result-bar');
  ok('结果页存在顶部导航条', !!bar);
  const backBtn = doc.querySelector('.result-bar .back-link');
  ok('顶部左侧有返回按钮', !!backBtn, backBtn && backBtn.textContent.trim());
  ok('返回按钮文案为「返回生成」', backBtn && backBtn.textContent.indexOf('返回生成') >= 0,
    backBtn && backBtn.textContent.trim());
  ok('结果页有放弃结果入口',
    [...doc.querySelectorAll('.result-bar button')].some(b => b.textContent.indexOf('放弃结果') >= 0));
  ok('底部也有返回入口',
    !!doc.querySelector('.result-bar-bottom .back-link'));

  // 2. 点击一次 → 直接回到生成页
  ok('结果页历史条目正确', win.history.state && win.history.state.ys === 'gen:result',
    win.history.state && win.history.state.ys);
  const backTop = doc.querySelector('.result-bar .back-link');
  backTop.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await sleep(800);

  ok('一次点击后仍在生成页（未跳首页）', st.page === 'gen', 'page=' + st.page);
  ok('已回到表单视图', st.genView === 'form', st.genView);
  ok('表单重新可见', doc.body.innerHTML.indexOf('选择节气') >= 0);

  // 3. 条件保留
  const after = st.form;
  ok('节气保留', after.tid === before.tid, before.tid + '→' + after.tid);
  ok('体质保留', after.cid === before.cid, before.cid + '→' + after.cid);
  ok('人群保留', after.group === before.group, before.group + '→' + after.group);
  ok('宴席类型保留', after.type === before.type, before.type + '→' + after.type);
  ok('慢病勾选保留', JSON.stringify(after.chronic) === JSON.stringify(before.chronic),
    JSON.stringify(after.chronic));
  ok('结果仍在缓存（可再查看）', !!st.banquet);
  ok('表单页出现「查看上次结果」',
    [...doc.querySelectorAll('button')].some(b => b.textContent.indexOf('查看上次结果') >= 0));

  // 4. 浏览器前进 → 还原结果（不重新生成）
  win.history.forward();
  await sleep(800);
  ok('浏览器前进回到结果页', st.genView === 'result' && st.page === 'gen', st.genView);

  // 浏览器后退 → 回到生成页
  win.history.back();
  await sleep(800);
  ok('浏览器后退回到生成页', st.genView === 'form' && st.page === 'gen', st.genView);

  // 5. 放弃结果弹窗：三个出口都要回到生成页
  const clickDiscard = () => {
    const b = [...doc.querySelectorAll('.result-bar button')]
      .find(x => (x.textContent || '').indexOf('放弃结果') >= 0);
    b.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  };
  const clickBox = label => {
    const b = [...doc.querySelectorAll('.el-message-box button')]
      .find(x => (x.textContent || '').trim().indexOf(label) >= 0);
    if (!b) return false;
    b.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
    return true;
  };

  win.history.forward(); await sleep(800);
  clickDiscard(); await sleep(600);
  ok('弹出放弃确认框', !!doc.querySelector('.el-message-box'));
  ok('确认框有「返回生成（保留结果）」', clickBox('返回生成（保留结果）'));
  await sleep(800);
  ok('弹窗确认后回到生成页', st.page === 'gen' && st.genView === 'form', st.page + '/' + st.genView);
  ok('确认后结果仍保留', !!st.banquet);

  win.history.forward(); await sleep(800);
  clickDiscard(); await sleep(600);
  ok('确认框有「放弃结果并清空」', clickBox('放弃结果并清空'));
  await sleep(900);
  ok('选「放弃结果」后回到生成页', st.page === 'gen' && st.genView === 'form', st.page + '/' + st.genView);
  ok('选「放弃结果」后清空缓存', !st.banquet);
  ok('放弃结果后条件仍保留', st.form.tid === before.tid && st.form.cid === before.cid);

  // 再生成一次，测试「关闭弹窗（X）」也回到生成页
  st.banquet = await win.API.generateBanquet({
    solar_term_id: before.tid, main_constitution_id: before.cid,
    special_group: before.group, banquet_type: before.type
  });
  st.genView = 'result';
  await sleep(700);
  clickDiscard(); await sleep(600);
  const closeX = doc.querySelector('.el-message-box__headerbtn');
  ok('弹窗有关闭按钮', !!closeX);
  if (closeX) closeX.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await sleep(900);
  ok('关闭弹窗后也回到生成页', st.page === 'gen' && st.genView === 'form', st.page + '/' + st.genView);
  ok('关闭弹窗后结果仍保留', !!st.banquet);

  // 6. 其他页面导航不受影响
  st.page = 'ing'; await sleep(500);
  ok('切到食材库正常', doc.body.innerHTML.indexOf('药食同源食材库') >= 0);
  const homeBtn = [...doc.querySelectorAll('button')].find(b => b.textContent.indexOf('返回首页') >= 0);
  ok('食材库有返回首页', !!homeBtn);
  homeBtn.dispatchEvent(new win.MouseEvent('click', { bubbles: true }));
  await sleep(500);
  ok('返回首页生效', st.page === 'home', st.page);
  ok('首页内容渲染', doc.body.innerHTML.indexOf('二十四节气') >= 0);

  // 从首页再进生成页，应落在表单而不是旧结果
  st.banquet = { solar_term: { name: 'x' }, main_constitution: { name: 'y' }, dishes: [] };
  st.page = 'gen';
  await sleep(600);
  ok('从别的页面进入生成页落在表单', st.genView === 'form', st.genView);
  st.banquet = null;

  const failed = checks.filter(c => !c[1]);
  console.log('\n=== 导航测试结果 ===');
  checks.forEach(c => console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] ? '  [' + c[2] + ']' : '')));
  console.log('\n通过 ' + (checks.length - failed.length) + '/' + checks.length);
  if (errors.length) console.log('运行时报错:\n' + errors.slice(0, 8).join('\n'));
  dom.window.close();
  process.exit(failed.length || errors.length ? 1 : 0);
})().catch(e => { console.error('测试异常:', e); process.exit(1); });
