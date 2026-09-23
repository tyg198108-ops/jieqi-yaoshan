/* 生成失败专项测试。
   背景：用户点「生成菜单」得到 "生成失败：Failed to fetch"，一句死文案，看不出该干什么。
   本测试覆盖：正常生成 / 后端全挂 / 接口 500 / file:// 打开时的路径补齐。 */
const { JSDOM, VirtualConsole } = require('jsdom');
const http = require('http');
const fs = require('fs');
const vm = require('vm');
const BASE = 'http://127.0.0.1:8000';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const fetchPage = p => new Promise((res, rej) => {
  http.get(BASE + p, r => { let d = ''; r.on('data', c => (d += c)); r.on('end', () => res(d)); }).on('error', rej);
});

const checks = [];
const ok = (name, cond, extra) => checks.push([name, !!cond, extra]);

async function boot(mode) {
  const html = await fetchPage('/');
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errors.push('jsdomError: ' + e.message));
  vc.on('error', (...a) => errors.push('error: ' + a.join(' ')));
  vc.on('warn', (...a) => errors.push('warn: ' + a.join(' ')));

  const calls = [];
  const dom = new JSDOM(html, {
    url: BASE + '/', runScripts: 'dangerously', resources: 'usable',
    pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.print = () => {};
      // jsdom 不带 fetch：正常模式借 Node 原生 fetch 打通真实后端
      if (mode === 'ok') {
        w.fetch = (u, o) => fetch(new URL(String(u), BASE).href, o);
      } else if (mode === 'down') {
        w.fetch = () => Promise.reject(new TypeError('Failed to fetch'));
      } else if (mode === 'http500') {
        w.fetch = (u) => {
          calls.push(String(u));
          return Promise.resolve({ ok: false, status: 500, text: () => Promise.resolve('{"detail":"内部错误"}') });
        };
      }
    }
  });
  const win = dom.window;
  for (let i = 0; i < 40 && !win.__state; i++) await sleep(300);
  return { win, doc: win.document, errors, calls };
}

async function tryGenerate(ctx) {
  const st = ctx.win.__state;
  st.roleKey = 'A'; st.showRolePicker = false; st.page = 'gen'; st.genView = 'form';
  await sleep(400);
  const btn = [...ctx.doc.querySelectorAll('button')].find(b => /生成|配膳|菜单/.test(b.textContent));
  if (btn) btn.click();
  await sleep(1500);
  return st;
}

(async () => {
  /* ---------- A. 正常生成 ---------- */
  {
    const ctx = await boot('ok');
    const st = await tryGenerate(ctx);
    ok('[正常] 生成成功出结果', st.genView === 'result' && st.banquet, st.genView);
    ok('[正常] 无错误卡片', !st.errBox);
    ctx.win.close();
  }

  /* ---------- B. 后端全挂 ---------- */
  {
    const ctx = await boot('down');
    const st = await tryGenerate(ctx);
    ok('[后端挂] 弹出错误卡片', !!st.errBox, st.genError);
    ok('[后端挂] 标题点明连不上', st.errBox && /连不上后端/.test(st.errBox.title), st.errBox && st.errBox.title);
    ok('[后端挂] 说明不出未校验结果', st.errBox && /不产出未校验结果/.test(st.errBox.why));
    ok('[后端挂] 步骤里给了启动方式', st.errBox && st.errBox.steps.some(s => /启动节气药膳师/.test(s)));
    ok('[后端挂] 步骤里给了访问地址', st.errBox && st.errBox.steps.some(s => /127\.0\.0\.1:8000/.test(s)));
    ok('[后端挂] 不再甩裸 Failed to fetch', !/Failed to fetch/.test(st.genError || ''));
    const html = ctx.doc.body.innerHTML;
    ok('[后端挂] 页面渲染出重试按钮', /重试/.test(html));
    ok('[后端挂] 页面渲染出检测按钮', /检测后端/.test(html));
    ok('[后端挂] 结果页未出现（不产出未校验结果）', st.genView === 'form');
    // 降级：首屏仍应能起来
    ok('[后端挂] 首屏回落到本地副本', st.dataSource === 'local', st.dataSource);
    ok('[后端挂] 食材库仍有数据', st.ingredients.length > 0, st.ingredients.length);
    ctx.win.close();
  }

  /* ---------- C. 接口 500 ---------- */
  {
    const ctx = await boot('http500');
    // 后端 500 时首屏会回落本地；这里直接调生成，验证错误卡片分类
    const st = ctx.win.__state;
    st.roleKey = 'A'; st.showRolePicker = false; st.page = 'gen'; st.genView = 'form';
    await sleep(300);
    ctx.win.API.generateBanquet({ solar_term_id: 16, main_constitution_id: 2, special_group: 'none', banquet_type: 'health' })
      .catch(e => {
        ok('[500] 错误被分类为 http', e.kind === 'http', e.kind);
        ok('[500] 带状态码 500', e.status === 500, e.status);
        ok('[500] 带后端 detail', /内部错误/.test(e.detail || ''), e.detail);
      });
    await sleep(1200);
    ctx.win.close();
  }

  /* ---------- D. file:// 下路径补齐 ---------- */
  {
    const src = fs.readFileSync('js/api.js', 'utf8');
    const sandbox = {
      location: { protocol: 'file:', origin: 'null' },
      localStorage: null,
      console,
      setTimeout, clearTimeout, Promise, AbortController,
      fetch: (u) => { sandbox.__lastUrl = String(u); return Promise.resolve({ ok: true, json: () => Promise.resolve({}) }); }
    };
    sandbox.window = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(src, sandbox);
    await sandbox.API.get('/api/health');
    ok('[file://] 相对路径被补成后端地址', sandbox.__lastUrl === 'http://127.0.0.1:8000/api/health', sandbox.__lastUrl);
    ok('[file://] isFileProtocol 为真', sandbox.API.isFileProtocol() === true);
  }

  /* ---------- E. 正常 http 下不加前缀 ---------- */
  {
    const src = fs.readFileSync('js/api.js', 'utf8');
    const sandbox = {
      location: { protocol: 'http:', origin: BASE },
      localStorage: null,
      console, setTimeout, clearTimeout, Promise, AbortController,
      fetch: (u) => { sandbox.__lastUrl = String(u); return Promise.resolve({ ok: true, json: () => Promise.resolve({}) }); }
    };
    sandbox.window = sandbox;
    vm.createContext(sandbox);
    vm.runInContext(src, sandbox);
    await sandbox.API.get('/api/health');
    ok('[http] 路径保持原样', sandbox.__lastUrl === '/api/health', sandbox.__lastUrl);
  }

  console.log('\n=== 生成失败处理测试 ===');
  let pass = 0;
  checks.forEach(c => {
    if (c[1]) pass++;
    console.log((c[1] ? '  PASS ' : '  FAIL ') + c[0] + (c[2] !== undefined ? '  [' + c[2] + ']' : ''));
  });
  console.log('\n' + pass + '/' + checks.length + ' 通过');
  process.exit(pass === checks.length ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
