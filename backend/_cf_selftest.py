"""云函数自我检验：模拟网关事件打全部接口。跑完记得删，或保留作为回归脚本。

用法：
  YS_API_ONLY=1 YS_DB_PATH=/tmp/yaoshan_test.db python _cf_selftest.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloud_entry import main  # noqa: E402


def call(method, path, qs='', body=None):
    ev = {'httpMethod': method, 'path': path,
          'headers': {'host': 'localhost'},
          'queryString': qs, 'body': body, 'isBase64Encoded': False}
    return main(ev, None)


def main_test():
    cases = [
        ('GET', '/api/health', ''),
        ('GET', '/api/solar-terms/', ''),
        ('GET', '/api/constitutions/', ''),
        ('GET', '/api/constitutions/questions', ''),
        ('GET', '/api/ingredients/', 'limit=3'),
        ('GET', '/api/dishes/', 'limit=3'),
        ('GET', '/api/config/profile', ''),
        ('GET', '/api/config/groups', ''),
        ('GET', '/api/config/rules', ''),
        ('GET', '/api/config/chronic', ''),
    ]
    ok = fail = 0
    for m, p, qs in cases:
        r = call(m, p, qs)
        try:
            d = json.loads(r['body'])
            n = len(d) if isinstance(d, list) else f'{len(d)} keys'
            flag = 'OK' if r['statusCode'] == 200 else 'FAIL'
        except Exception as e:
            n, flag = str(e)[:60], 'BADJSON'
        print(f'[{flag}] {m} {p}?{qs} -> {r["statusCode"]} len={len(r["body"])} {n}')
        ok, fail = (ok + 1, fail) if flag == 'OK' else (ok, fail + 1)

    print('\n--- 三场景生成 ---')
    for bt in ['health', 'family', 'business']:
        payload = {
            'solar_term_id': 1, 'main_constitution_id': 1, 'special_group': 'none',
            'banquet_type': bt,
            'banquet_scale': 'banquet' if bt == 'health' else None,
            'headcount': 10,
        }
        t0 = time.time()
        r = call('POST', '/api/banquet/generate', '', json.dumps(payload, ensure_ascii=False))
        dt = time.time() - t0
        try:
            d = json.loads(r['body'])
            dishes = d.get('dishes') or []
            good = r['statusCode'] == 200
            print(f"[{'OK' if good else 'FAIL'}] POST generate {bt} -> {r['statusCode']} "
                  f'菜数={len(dishes)} unmet={d.get("unmet")} {dt:.2f}s')
            if good:
                ok += 1
            else:
                fail += 1
                print('   body:', r['body'][:300])
        except Exception as e:
            fail += 1
            print('[BADJSON]', r['statusCode'], str(e)[:80], r['body'][:200])

    print('\n--- 异常输入不应崩库 ---')
    bad = ['{}', '{"solar_term_id":999,"banquet_type":"health"}', 'not json']
    for b in bad:
        r = call('POST', '/api/banquet/generate', '', b)
        exp = 400 <= r['statusCode'] < 600
        print(f"[{'OK' if exp else 'FAIL'}] bad body -> {r['statusCode']} "
              f"{r['body'][:90]}")
        ok, fail = (ok + 1, fail) if exp else (ok, fail + 1)

    print(f'\n=== 通过 {ok} / 失败 {fail} ===')
    return fail


if __name__ == '__main__':
    sys.exit(1 if main_test() else 0)
