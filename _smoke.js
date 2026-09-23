/* 前端冒烟：用 jsdom 真实加载页面（含 Vue / Element Plus），
   检查渲染结果、捕获运行时报错。后端需先启动在 127.0.0.1:8000。 */
const { JSDOM, VirtualConsole } = require('jsdom');
const http = require('http');

const BASE = 'http://127.0.0.1:8000';

function fetchPage(path) {
  return new Promise((resolve, reject) => {
    http.get(BASE + path, res => {
      let d = '';
      res.on('data', c => (d += c));
      res.on('end', () => resolve(d));
    }).on('error', reject);
  });
}

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
      // jsdom 没有 fetch：用 Node 内置 fetch 做一层最小 shim
      window.fetch = (url, opts) =>
        globalThis.fetch(new URL(url, BASE).href, opts).then(r =>
          r.text().then(t => ({
            ok: r.ok,
            status: r.status,
            json: () => Promise.resolve(JSON.parse(t)),
            text: () => Promise.resolve(t),
          }))
        );
      window.print = () => {};
    },
  });

  await new Promise(r => setTimeout(r, 3500));
  const doc = dom.window.document;
  const app = doc.getElementById('app');
  const text = (app && app.textContent ? app.textContent : '').replace(/\s+/g, ' ').trim();

  console.log('--- 渲染文本片段 ---');
  console.log(text.slice(0, 400));
  console.log('\n--- 关键检查 ---');
  const checks = [
    ['页面已挂载（非空）', text.length > 50],
    ['无「数据加载失败」', text.indexOf('数据加载失败') < 0],
    ['角色选择弹窗出现', text.indexOf('先用哪个身份') >= 0],
    ['三个角色可见', text.indexOf('餐饮门店') >= 0 && text.indexOf('从业者') >= 0 && text.indexOf('家庭用户') >= 0],
    ['节气数据已渲染', /秋分|春分|立春/.test(text)],
  ];
  checks.forEach(([n, ok]) => console.log((ok ? '[OK]   ' : '[FAIL] ') + n));

  console.log('\n--- 运行时错误 ---');
  if (errors.length === 0) console.log('无');
  else errors.slice(0, 10).forEach(e => console.log(e.slice(0, 300)));

  /* ---- 第二阶段：切到 C 家庭 → 生成 → 验证角色差异 ---- */
  const w = dom.window;
  const res = await w.API.generateBanquet({
    solar_term_id: 16, main_constitution_id: 2,
    special_group: 'pregnant', banquet_type: 'health',
  });
  const setRole = key => {
    w.__state.role.set(key);
    w.__state.roleKey = key;
    w.__state.page = 'gen';
    w.__state.showRolePicker = false;
    w.__state.banquet = res;
    w.__state.genView = 'result';   // 结果视图由 genView 控制，banquet 只是缓存
  };
  const textOf = () => {
    const a = doc.getElementById('app');
    return (a && a.textContent ? a.textContent : '').replace(/\s+/g, ' ').trim();
  };

  setRole('C');
  await new Promise(r => setTimeout(r, 1200));
  const tC = textOf();
  console.log('\n--- C 家庭角色 ---');
  [
    /* 席单结构由后端场景决定，前端不再按角色裁剪；C 端看到的是完整的分组席单。
       断言随养生宴 17 道结构（冷菜6+热菜8+汤1+点心/主食1+茶饮1）同步更新过。 */
    ['按场景出完整席单', tC.indexOf('养生宴') >= 0 && /17道/.test(tC)],
    ['显示席面构成', tC.indexOf('席面构成') >= 0],
    ['云端「保存方案」可用', tC.indexOf('保存方案') >= 0],
    ['C 端隐藏规则出处', tC.indexOf('出处：') < 0],
    ['C 端仍显示安全汇总', tC.indexOf('安全校验汇总') >= 0],
    ['C 端仍显示疗程建议', tC.indexOf('疗程建议') >= 0],
  ].forEach(([n, ok]) => console.log((ok ? '[OK]   ' : '[FAIL] ') + n));
  console.log('片段：' + tC.slice(0, 160));

  setRole('A');
  await new Promise(r => setTimeout(r, 1200));
  const tA = textOf();
  console.log('\n--- A 从业者角色 ---');
  [
    ['显示完整分组席单', /迎宾冷菜|冷菜/.test(tA)],
    ['A 端显示规则出处', tA.indexOf('出处：') >= 0],
    ['A 端显示席面名', tA.indexOf('节气养生宴') >= 0],
  ].forEach(([n, ok]) => console.log((ok ? '[OK]   ' : '[FAIL] ') + n));
  console.log('片段：' + tA.slice(0, 160));

  const failed = checks.filter(c => !c[1]).length;
  dom.window.close();
  process.exit(failed > 0 ? 1 : 0);
})();
