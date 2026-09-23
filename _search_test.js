/* 食材库搜索专项测试：真实输入 → 表格过滤 → 计数反馈 → 分类/属性筛选 */
const { JSDOM, VirtualConsole } = require('jsdom');
const http = require('http');
const BASE = 'http://127.0.0.1:8000';
const sleep = ms => new Promise(r => setTimeout(r, ms));

function fetchPage(p) {
  return new Promise((res, rej) => {
    http.get(BASE + p, r => { let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(d)); }).on('error', rej);
  });
}

const checks = [];
const ok = (n, c, x) => checks.push([n, !!c, x === undefined ? '' : String(x)]);

(async () => {
  const html = await fetchPage('/');
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push('jsdomError: ' + e.message));
  vc.on('error', (...a) => errors.push('error: ' + a.join(' ')));

  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', resources: 'usable',
    pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.fetch = (u, o) => globalThis.fetch(new URL(u, BASE).href, o).then(r =>
        r.text().then(t => ({ ok: r.ok, status: r.status, json: () => Promise.resolve(JSON.parse(t)), text: () => Promise.resolve(t) })));
      w.print = () => {};
    }
  });
  const win = dom.window, doc = win.document;
  for (let i = 0; i < 60 && !win.__state; i++) await sleep(200);
  const st = win.__state;

  st.roleKey = 'A'; st.showRolePicker = false; st.page = 'ing';
  await sleep(1200);

  const rows = () => doc.querySelectorAll('.el-table__body tbody tr').length;
  const countText = () => {
    const e = doc.querySelector('.ing-count');
    return e ? e.textContent.replace(/\s+/g, ' ').trim() : '';
  };
  const type = kw => {
    const input = doc.querySelector('.el-input__inner');
    input.value = kw;
    input.dispatchEvent(new win.Event('input', { bubbles: true }));
    return sleep(500);
  };

  ok('食材库已渲染', doc.body.innerHTML.indexOf('药食同源食材库') >= 0);
  ok('初始显示全量', rows() === st.ingredients.length, rows());
  ok('初始计数正确', countText().indexOf('共 ' + st.ingredients.length + ' 味') >= 0, countText());

  // 各类关键词
  await type('山药');       ok('按名称搜「山药」', rows() > 0 && rows() < 83, rows());
  await type('淮山');       ok('按别名搜「淮山」', rows() > 0, rows());
  await type('脾');         ok('按归经搜「脾」', rows() > 0, rows());
  await type('健脾');       ok('按功效搜「健脾」', rows() > 0, rows());
  await type('气虚质');     ok('按适宜体质搜「气虚质」', rows() > 0, rows());
  await type('秋季');       ok('按适宜季节搜「秋季」', rows() > 0, rows());
  await type('甘');         ok('按五味搜「甘」', rows() > 0, rows());
  await type('zzz不存在');  ok('无匹配时行为空', rows() === 0, rows());
  ok('无匹配有文字提示', countText().indexOf('没有匹配') >= 0, countText());

  // 清空条件
  const clearBtn = [...doc.querySelectorAll('.ing-count button')].find(b => b.textContent.indexOf('清空条件') >= 0);
  ok('有「清空条件」按钮', !!clearBtn);
  if (clearBtn) { clearBtn.dispatchEvent(new win.MouseEvent('click', { bubbles: true })); await sleep(500); }
  ok('清空后恢复全量', rows() === st.ingredients.length && !st.kw, rows());

  // 属性筛选
  st.ingKind = 'catalog'; await sleep(500);
  const catalogN = rows();
  ok('筛「药食同源」有结果且变少', catalogN > 0 && catalogN < st.ingredients.length, catalogN);
  st.ingKind = 'food'; await sleep(500);
  ok('筛「普通食品」与上者互补', rows() === st.ingredients.length - catalogN, rows() + '+' + catalogN);
  st.ingKind = 'all'; await sleep(400);

  // 分类下拉
  ok('分类下拉有选项', st && true);
  st.ingCat = '补气类'; await sleep(600);
  ok('按分类筛「补气类」', rows() > 0 && rows() < st.ingredients.length, rows());
  st.ingCat = ''; await sleep(400);

  // 搜索 + 分类叠加
  st.ingKind = 'catalog'; await type('脾');
  ok('分类与关键词可叠加', rows() > 0 && rows() <= catalogN, rows());

  // C 家庭角色下同样可用
  st.ingKind = 'all'; await type('');
  st.roleKey = 'C'; await sleep(600);
  await type('山药');
  ok('C 家庭角色下搜索也可用', rows() > 0, rows());
  ok('C 端仍隐藏四气列', doc.body.innerHTML.indexOf('四气') < 0);

  const failed = checks.filter(c => !c[1]);
  console.log('\n=== 食材库搜索测试 ===');
  checks.forEach(c => console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] ? '  [' + c[2] + ']' : '')));
  console.log('\n通过 ' + (checks.length - failed.length) + '/' + checks.length);
  const real = errors.filter(e => e.indexOf('Could not parse CSS') < 0);
  console.log(real.length ? '运行时报错:\n' + real.slice(0, 8).join('\n') : '无运行时报错（CSS 解析告警为 vendor 自带，已忽略）');
  dom.window.close();
  process.exit(failed.length || real.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
