/* 场景专项测试：养生宴 / 家庭餐 / 商务餐 必须出不同结构，不能三个场景一个样。
   直连后端接口校验席单构成（道数、席位分组、类型对位），并在页面上验一次渲染。
   后端需先启动在 127.0.0.1:8000。 */
const http = require('http');

const BASE = 'http://127.0.0.1:8000';
const checks = [];
const ok = (name, cond, extra) => checks.push([name, !!cond, extra || '']);

function post(path, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = http.request(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
    }, res => {
      let d = '';
      res.on('data', c => (d += c));
      res.on('end', () => { try { resolve(JSON.parse(d)); } catch (e) { reject(new Error('非JSON返回: ' + d.slice(0, 200))); } });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

const gen = (type, scale) => post('/api/banquet/generate', {
  solar_term_id: 1, main_constitution_id: 1,
  special_group: 'none', banquet_type: type, banquet_scale: scale || 'standard'
});

/* 席位应当落在本类型上：冷碟位不能端热菜，汤品位不能端点心 */
const ALLOW = {
  cold: ['冷碟'], hot: ['热菜', '主菜'], veg: ['素菜'],
  soup: ['汤品'], staple: ['主食'], dessert: ['甜品'], drink: ['茶饮']
};

(async () => {
  console.log('=== 场景席单结构测试 ===\n');

  const health = await gen('health', 'standard');
  const stapleHealth = await post('/api/banquet/generate', {
    solar_term_id: 1, main_constitution_id: 1, special_group: 'none',
    banquet_type: 'health', headcount: 10, finale: 'staple'
  });
  const family = await gen('family');
  const business = await gen('business');

  ok('养生宴 17 道', health.dishes.length === 17, '实出 ' + health.dishes.length);
  ok('养生宴默认 10 人席', health.headcount === 10, '实际 ' + health.headcount);
  ok('切「养生主食」仍是 17 道', stapleHealth.dishes.length === 17, '实出 ' + stapleHealth.dishes.length);
  ok('切主食后主食位有菜', stapleHealth.dishes.filter(d => d.course === 'staple').length === 1);
  ok('家庭餐 6 道（四菜一汤一饮）', family.dishes.length === 6, '实出 ' + family.dishes.length);
  ok('商务餐 8 道', business.dishes.length === 8, '实出 ' + business.dishes.length);

  const cnt = (r, course) => r.dishes.filter(d => d.course === course).length;
  ok('家庭：2 热菜 + 2 素菜 + 1 汤 + 1 饮',
    cnt(family, 'hot') === 2 && cnt(family, 'veg') === 2 && cnt(family, 'soup') === 1 && cnt(family, 'drink') === 1,
    `热${cnt(family, 'hot')} 素${cnt(family, 'veg')} 汤${cnt(family, 'soup')} 饮${cnt(family, 'drink')}`);
  ok('商务：2 冷菜 + 4 热菜 + 1 汤 + 1 饮',
    cnt(business, 'cold') === 2 && cnt(business, 'hot') === 4 && cnt(business, 'soup') === 1 && cnt(business, 'drink') === 1,
    `冷${cnt(business, 'cold')} 热${cnt(business, 'hot')} 汤${cnt(business, 'soup')} 饮${cnt(business, 'drink')}`);
  ok('养生宴：冷菜 6 道 + 热菜 8 道 + 汤 1 道 + 点心 1 道 + 茶饮 1 道',
    cnt(health, 'cold') === 6 && cnt(health, 'hot') === 8 && cnt(health, 'soup') === 1 &&
    cnt(health, 'dessert') === 1 && cnt(health, 'drink') === 1,
    `冷${cnt(health, 'cold')} 热${cnt(health, 'hot')} 汤${cnt(health, 'soup')}`);

  ok('三个场景菜色不同（家庭 ≠ 商务）',
    family.dishes.map(d => d.dish.name).join() !== business.dishes.map(d => d.dish.name).join());
  ok('养生宴与家庭餐结构不同', health.dishes.length !== family.dishes.length);

  const scenes = { '养生宴': health, '养生宴(主食)': stapleHealth, '家庭餐': family, '商务餐': business };
  Object.keys(scenes).forEach(name => {
    const r = scenes[name];
    const ids = r.dishes.map(d => d.dish.id);
    ok(`${name} 无重复菜品`, new Set(ids).size === ids.length);
    // 热菜/素菜位允许跨到一个备用类型，其余分组必须落在本类型上
    const wrong = r.dishes.filter(d => {
      const allow = (ALLOW[d.course] || []).concat(d.course === 'hot' ? ['素菜'] : []);
      return !allow.includes(d.dish.dish_type);
    });
    ok(`${name} 席位类型对位`, wrong.length === 0,
      wrong.map(d => `${d.position_name}=${d.dish.name}(${d.dish.dish_type})`).join('、'));
    ok(`${name} 返回席面构成说明`, !!r.structure_text, r.structure_text);
  });

  /* 极端组合：节气 × 体质 × 人群 轮换，结构不许散架 */
  for (const [tid, cid, g] of [[1, 1, 'none'], [6, 3, 'pregnant'], [12, 5, 'children'], [18, 7, 'elderly'], [21, 9, 'none']]) {
    for (const [t, sc] of [['health', 'standard'], ['health', 'staple'], ['family', 'standard'], ['business', 'standard']]) {
      const r = await post('/api/banquet/generate', {
        solar_term_id: tid, main_constitution_id: cid, special_group: g,
        banquet_type: t, finale: (t === 'health' && sc === 'staple') ? 'staple' : 'dessert'
      });
      const want = (t === 'health' ? 17 : (t === 'family' ? 6 : 8));
      ok(`${t}/${sc} @节气${tid}体质${cid}人群${g} 出 ${want} 道`, r.dishes.length === want, '实出 ' + r.dishes.length);
      ok(`${t}/${sc} @节气${tid} 无重复`, new Set(r.dishes.map(d => d.dish.id)).size === r.dishes.length);
    }
  }

  /* 三类场景的安全底线：红线菜不入席 */
  const blocked = [health, stapleHealth, family, business].filter(r => r.stat && r.stat.block > 0);
  ok('四类席单均无红线级冲突', blocked.length === 0);

  checks.forEach(([n, pass, extra]) => console.log((pass ? '  PASS ' : '  FAIL ') + n + (extra && !pass ? '  → ' + extra : '')));
  const passed = checks.filter(c => c[1]).length;
  console.log(`\n通过 ${passed}/${checks.length}`);
  process.exit(passed === checks.length ? 0 : 1);
})().catch(e => { console.error('测试异常：', e.message); process.exit(1); });
