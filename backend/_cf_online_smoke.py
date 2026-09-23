"""线上冒烟测试：直接打 CloudBase 网关，验证部署是否真的可用。

用法（本机 python 即可，无需装依赖）：
    python backend/_cf_online_smoke.py
    python backend/_cf_online_smoke.py https://自定义域名

为什么需要它：
    只看 /api/health 返回 200 不代表部署成功 —— Base 里曾经出现过 health 通、
    但 list 路由 404、数据库空库（0 条）的假上线。这个脚本卡三件事：
    1) 各 GET 路由是否可达 2) 数据量是否与本地库一致 3) 三场景生成是否还出得来。

两个反直觉的坑，改这个脚本时别踩回去：
    · 列表路由必须带尾斜杠 /api/ingredients/，不带会被 307 重定向，
      urllib 跟随重定向但 curl 不跟随，于是 curl 看着像 404。
    · 别用 print 看 curl 的中文输出判断乱码 —— Git Bash 控制台按 cp1252 渲染
      UTF-8 字节，屏幕上是乱的，实际传输没问题。这里统一 decode('utf-8', strict)。
"""
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = 'https://jieqi-yaoshan-d7gd6ypfscd10299f-1308818540.ap-shanghai.app.tcloudbase.com'
BASE = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
    'YS_API_BASE', DEFAULT_BASE)).rstrip('/')
API = BASE + '/api'

_LOCAL_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yaoshan.db')

_fails = []


def _ok(label, cond, detail=''):
    mark = 'PASS' if cond else 'FAIL'
    if not cond:
        _fails.append(label)
    print(f'  [{mark}] {label}{("  " + detail) if detail else ""}')


def get(path):
    with urllib.request.urlopen(API + path, timeout=90) as r:
        return json.loads(r.read().decode('utf-8'))  # strict，编码有问题直接抛


def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        API + path, data=data,
        headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode('utf-8'))


def check_health():
    print('\n[1] 健康检查')
    try:
        t = time.time()
        d = get('/health')
        _ok('/api/health 可达', True, f'{time.time() - t:.1f}s')
        _ok('status=ok', d.get('status') == 'ok', str(d.get('version')))
        _ok('运行在 api-only 模式', d.get('mode') == 'api-only')
    except Exception as e:
        _ok('/api/health 可达', False, repr(e))
        raise SystemExit('\n服务不可达，后续检查跳过。')


def check_routes():
    print('\n[2] GET 路由可达性')
    routes = {
        '/solar-terms/': '节气',
        '/constitutions/': '体质',
        '/ingredients/': '食材',
        '/dishes/': '菜品',
        '/config/profile': '产品配置',
        '/config/groups': '人群标签',
        '/solar-terms/current': '当前节气',
    }
    data = {}
    for path, label in routes.items():
        try:
            r = get(path)
            n = len(r) if isinstance(r, list) else 1
            _ok(f'{label:<6} {path:<22}', bool(r), f'{n} 条')
            data[path] = r
        except urllib.error.HTTPError as e:
            _ok(f'{label:<6} {path:<22}', False, f'HTTP {e.code}')
    return data


def check_volume(data):
    """数据量必须和本地库一致 —— 这是判断 db_bootstrap 是否真的自举成功的唯一硬指标。

    曾经出现 health 200、但云函数 /tmp 是空的导致数据库只有几条的情况，
    页面上表现为「食材数 195（本地降级）」而不是 207。"""
    print('\n[3] 数据量 vs 本地库')
    online = {
        'ingredients': len(data.get('/ingredients/') or []),
        'dishes': len(data.get('/dishes/') or []),
        'solar_terms': len(data.get('/solar-terms/') or []),
        'constitutions': len(data.get('/constitutions/') or []),
    }
    if not os.path.exists(_LOCAL_DB):
        print(f'  [SKIP] 本地库不存在：{_LOCAL_DB}')
        return
    c = sqlite3.connect(_LOCAL_DB)
    local = {t: c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
             for t in online}
    c.close()
    for t, n in online.items():
        _ok(f'{t:<15} 线上 {n} / 本地 {local[t]}', n == local[t])


def check_generate():
    """三场景硬结构 + 安全门。这是产品的核心卖点，任何一项退化都要拦住。"""
    print('\n[4] 宴席生成（三场景 + 特殊人群）')
    try:
        cons = {c['name'].replace('质', ''): c['id']
                for c in get('/constitutions/')}
    except Exception as e:
        _ok('取体质列表', False, repr(e))
        return

    cases = [
        ('养生宴 10人席', dict(solar_term_id=16,
         main_constitution_id=cons['气虚'], banquet_type='health', headcount=10),
         17, dict(cold=6, hot=8, soup=1, dessert=1, drink=1)),
        ('家庭餐 4人', dict(solar_term_id=16,
         main_constitution_id=cons['阴虚'], banquet_type='family', headcount=4),
         6, dict(hot=2, veg=2, soup=1, drink=1)),
        ('商务宴 8人', dict(solar_term_id=16,
         main_constitution_id=cons['平和'], banquet_type='business', headcount=8),
         8, dict(cold=2, hot=4, soup=1, drink=1)),
        ('养生宴+孕妇', dict(solar_term_id=16, main_constitution_id=cons['平和'],
                         banquet_type='health', headcount=6, special_group='pregnant'),
         17, None),
        ('立春/阳虚', dict(solar_term_id=1, main_constitution_id=cons['阳虚'],
                       banquet_type='health', headcount=10), 17, None),
    ]

    for label, payload, want_count, want_stat in cases:
        try:
            t = time.time()
            r = post('/banquet/generate', payload)
            dt = time.time() - t
            got = len(r.get('dishes', []))
            _ok(f'{label} 出菜 {got} 道（期望 {want_count}）',
                got == want_count, f'{dt:.1f}s · {r.get("structure_label")}')
            if want_stat:
                _ok(f'{label} 分组结构', r.get('course_stat') == want_stat,
                    str(r.get('course_stat')))
            _ok(f'{label} 席位要求全满足', not r.get('unmet'), str(r.get('unmet')))
            stat = r.get('stat') or {}
            _ok(f'{label} 无禁忌硬阻断',
                stat.get('block', 0) == 0, str(stat))
            if payload.get('special_group'):
                sw = ' '.join(r.get('safety_warnings') or [])
                _ok('孕妇禁忌告警已触发', '孕妇' in sw)
        except urllib.error.HTTPError as e:
            _ok(label, False, f'HTTP {e.code} {e.read().decode("utf-8", "replace")[:200]}')
        except Exception as e:
            _ok(label, False, repr(e))


def main():
    print(f'目标：{API}')
    check_health()
    data = check_routes()
    check_volume(data)
    check_generate()
    print('\n' + '=' * 56)
    if _fails:
        print(f'FAILED {len(_fails)} 项：')
        for f in _fails:
            print('  -', f)
        raise SystemExit(1)
    print('全部通过 —— 后端部署健康，可以上传/更新静态托管了。')


if __name__ == '__main__':
    main()
