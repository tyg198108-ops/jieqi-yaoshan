/* 断网降级测试：强制所有 /api 请求失败，验证会回落到 app-data.js 且能用。
   （曾踩坑：app-data.js 用顶层 const 声明，window.X 取不到 → 降级路径一直是死的） */
const { JSDOM, VirtualConsole } = require('jsdom');
const http = require('http');
const BASE = 'http://127.0.0.1:8000';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const fetchPage = p => new Promise((res, rej) => {
  http.get(BASE + p, r => { let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(d)); }).on('error', rej);
});

(async () => {
  const html = await fetchPage('/');
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push('jsdomError: ' + e.message));
  vc.on('error', (...a) => errors.push('error: ' + a.join(' ')));
  vc.on('warn', (...a) => errors.push('warn: ' + a.join(' ')));

  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', resources: 'usable',
    pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.print = () => {};
      // 后端全挂
      w.fetch = () => Promise.reject(new Error('模拟后端不可用'));
    }
  });
  const win = dom.window, doc = win.document;
  for (let i = 0; i < 40 && !win.__state; i++) await sleep(300);

  const st = win.__state;
  const checks = [
    ['应用能启动（不再白屏）', !!st],
    ['数据源标记为 local', st && st.dataSource === 'local', st && st.dataSource],
    ['食材有数据', st && st.ingredients.length > 0, st && st.ingredients.length],
    ['菜品有数据', st && st.dishes.length > 0, st && st.dishes.length],
    ['页面未显示「数据加载失败」', doc.body.innerHTML.indexOf('数据加载失败') < 0]
  ];

  if (st) {
    st.roleKey = 'A'; st.showRolePicker = false; st.page = 'ing'; st.kw = '山药';
    await sleep(900);
    const rows = doc.querySelectorAll('.el-table__body tbody tr').length;
    checks.push(['降级下搜索仍可用', rows > 0, rows + ' 行']);
  }

  console.log('\n=== 断网降级测试 ===');
  checks.forEach(c => console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] !== undefined ? '  [' + c[2] + ']' : '')));
  const real = errors.filter(e => e.indexOf('Could not parse CSS') < 0 && e.indexOf('后端不可用') < 0);
  console.log(real.length ? '报错:\n' + real.slice(0, 5).join('\n') : '无异常');
  dom.window.close();
  process.exit(checks.some(c => !c[1]) ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
