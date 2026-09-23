/* 养生宴硬结构专项测试（胡老师 2026-09-23 定的口径）：
   冷菜 6 道 3 荤 3 素 / 热菜 8 道必覆虾·鱼·牛羊猪·鸡·蔬菜五类且技法尽量多样 /
   药膳汤 1 道带药材配伍与功效 / 点心或主食 1 道 / 茶饮 1 道带季节功效宜忌 / 默认 10 人席。
   后端需先启动在 127.0.0.1:8000。 */
const http = require('http');

const BASE = 'http://127.0.0.1:8000';
const checks = [];
const ok = (n, c, e) => checks.push([n, !!c, e || '']);

const post = (path, body) => new Promise((resolve, reject) => {
  const data = JSON.stringify(body);
  const req = http.request(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
  }, res => {
    let d = '';
    res.on('data', c => (d += c));
    res.on('end', () => { try { resolve(JSON.parse(d)); } catch (e) { reject(new Error('非JSON: ' + d.slice(0, 200))); } });
  });
  req.on('error', reject);
  req.write(data);
  req.end();
});

const gen = (opt = {}) => post('/api/banquet/generate', Object.assign({
  solar_term_id: 1, main_constitution_id: 1, special_group: 'none',
  banquet_type: 'health', headcount: 10, finale: 'dessert'
}, opt));

const seat = (r, name) => r.dishes.filter(d => d.position_name === name)[0];

/* 五类必覆的席位 */
const REQUIRED = [
  ['河鲜虾馔', '虾类'], ['江河鱼馔', '鱼类'], ['畜肉大菜', '牛羊猪'],
  ['禽馔一味', '鸡鸭禽'], ['时令蔬菜', '蔬菜'],
];

(async () => {
  console.log('=== 养生宴硬结构测试 ===\n');
  const r = await gen();

  ok('总道数 17 道', r.dishes.length === 17, '实出 ' + r.dishes.length);
  ok('默认 10 人席', r.headcount === 10, '实际 ' + r.headcount);

  const cold = r.dishes.filter(d => d.course === 'cold');
  const hot = r.dishes.filter(d => d.course === 'hot');
  ok('冷菜 6 道', cold.length === 6, '实出 ' + cold.length);
  ok('热菜 8 道', hot.length === 8, '实出 ' + hot.length);
  ok('汤品 1 道', r.dishes.filter(d => d.course === 'soup').length === 1);
  ok('饮品 1 道', r.dishes.filter(d => d.course === 'drink').length === 1);

  const meatCold = cold.filter(d => d.require_label === '荤');
  ok('冷菜含 3 道荤席位', meatCold.length === 3, '实出 ' + meatCold.length);

  REQUIRED.forEach(([seatName, tag]) => {
    const d = seat(r, seatName);
    ok(`${seatName} 席位存在`, !!d);
    if (d) ok(`${seatName} 是${tag}`, (d.food_tag || '').indexOf(tag) >= 0, d.food_tag);
  });

  /* 五类实际去重后是否齐 */
  const tags = new Set();
  hot.forEach(d => (d.food_tag || '').split(' + ').forEach(t => tags.add(t)));
  ['虾类', '鱼类', '牛羊猪', '鸡鸭禽', '蔬菜'].forEach(t =>
    ok(`热菜覆盖 ${t}`, tags.has(t), [...tags].join('/')));

  const methods = hot.map(d => d.method).filter(Boolean);
  ok('热菜技法 ≥3 种', new Set(methods).size >= 3, [...new Set(methods)].join('/'));

  const soup = r.dishes.filter(d => d.course === 'soup')[0];
  ok('药膳汤标了药材配伍', !!soup.pairing, soup.pairing);
  ok('药膳汤给了功效说明', !!soup.dish.efficacy_chinese);

  const drink = r.dishes.filter(d => d.course === 'drink')[0];
  ok('茶饮注明适宜季节', /适宜季节/.test(drink.drink_note || ''), drink.drink_note);
  ok('茶饮注明功效', /功效/.test(drink.drink_note || ''));
  ok('茶饮注明饮用宜忌', /饮用宜忌|体质核对/.test(drink.drink_note || ''));

  /* 收尾一道可切换点心 / 主食 */
  const staple = await gen({ finale: 'staple' });
  const tailS = staple.dishes.filter(d => d.course === 'staple');
  ok('切「养生主食」后出主食 1 道', tailS.length === 1, staple.dishes.map(d => d.course).join(','));
  ok('切主食后点心位消失', staple.dishes.filter(d => d.course === 'dessert').length === 0);

  /* 人数可变 */
  const small = await gen({ headcount: 6 });
  ok('人数可设为 6', small.headcount === 6, String(small.headcount));
  ok('按人数给出备餐说明', /6 人席/.test(small.time_schedule));

  /* 多节气 / 体质 / 人群轮换，结构不能散架 */
  for (const [tid, cid, g] of [[1, 1, 'none'], [4, 2, 'none'], [8, 4, 'children'],
                               [12, 5, 'none'], [16, 6, 'pregnant'], [20, 8, 'elderly'], [23, 9, 'none']]) {
    const x = await gen({ solar_term_id: tid, main_constitution_id: cid, special_group: g });
    const t = new Set();
    x.dishes.filter(d => d.course === 'hot').forEach(d => (d.food_tag || '').split(' + ').forEach(v => t.add(v)));
    const cover = ['虾类', '鱼类', '牛羊猪', '鸡鸭禽', '蔬菜'].every(v => t.has(v));
    ok(`节气${tid}体质${cid} 17 道`, x.dishes.length === 17, '实出 ' + x.dishes.length);
    ok(`节气${tid}体质${cid} 五类必覆`, cover, [...t].join('/'));
    ok(`节气${tid} 无重复菜`, new Set(x.dishes.map(d => d.dish.id)).size === x.dishes.length);
    ok(`节气${tid} 无红线`, !x.stat || x.stat.block === 0, JSON.stringify(x.stat));
    console.log(`  · 节气${tid} 未满足席位: ${x.unmet.map(u => u.seat + '(' + u.label + ')').join('、') || '无'}`);
  }

  console.log('');
  let pass = 0;
  checks.forEach(([n, p, extra]) => {
    if (p) pass++;
    console.log((p ? '  PASS ' : '  FAIL ') + n + (!p && extra ? '  → ' + extra : ''));
  });
  console.log(`\n通过 ${pass}/${checks.length}`);
  process.exit(pass === checks.length ? 0 : 1);
})().catch(e => { console.error('测试异常：', e.message); process.exit(1); });
