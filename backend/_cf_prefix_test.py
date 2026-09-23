# -*- coding: utf-8 -*-
"""网关路径兼容性测试。

背景：CloudBase 的 HTTP 网关配了 `/api/*` 路由后，转发给云函数的 event.path
有可能已经被剥掉前缀（`/api/health` → `/health`），此时 FastAPI 回 404，
而且这个 404 跟"接口不存在"完全一样，在线上极难分辨。

cloud_adapter.handle 里加了 404 反向重试：带 /api 和不带 /api 都试一遍。
本测试把两种形态都跑一遍，确保网关不管怎么处理都能接通。

用法：YS_API_ONLY=1 YS_DB_PATH=/tmp/xxx.db python _cf_prefix_test.py
"""
import json, os
os.environ.setdefault('YS_API_ONLY', '1')
os.environ.setdefault('YS_DB_PATH', '/tmp/yaoshan_prefix.db')
from cloud_entry import main  # noqa: E402



def call(method, path, body=None):
    return main({'httpMethod': method, 'path': path,
                 'headers': {'host':'gw','content-type':'application/json'},
                 'queryString':'', 'body': body, 'isBase64Encoded': False}, None)

cases = [
    ('GET',  '/api/health'),        # 带前缀（正常）
    ('GET',  '/health'),            # 网关剥掉前缀
    ('GET',  '/api/solar-terms/'),
    ('GET',  '/solar-terms/'),
    ('GET',  '/api/constitutions/'),
    ('GET',  '/constitutions/'),
    ('GET',  '/api/config/profile'),
    ('GET',  '/config/profile'),
]
ok = fail = 0
for m, p in cases:
    r = call(m, p)
    flag = 'OK' if r['statusCode'] == 200 else 'FAIL'
    print('[%s] %-28s -> %s %s' % (flag, p, r['statusCode'], r['body'][:60].replace('\n',' ')))
    ok += (flag=='OK'); fail += (flag=='FAIL')

# POST 生成（剥前缀）
payload = {'solar_term_id':1,'main_constitution_id':1,'special_group':'none',
           'banquet_type':'health','banquet_scale':'standard','headcount':10,'finale':'dessert'}
for p in ['/api/banquet/generate', '/banquet/generate']:
    r = call('POST', p, json.dumps(payload, ensure_ascii=False))
    try:
        n = len(json.loads(r['body']).get('dishes') or [])
    except Exception:
        n = -1
    flag = 'OK' if r['statusCode']==200 and n else 'FAIL'
    print('[%s] POST %-24s -> %s 菜数=%s' % (flag, p, r['statusCode'], n))
    ok += (flag=='OK'); fail += (flag=='FAIL')

print('\n=== 通过 %d / 失败 %d ===' % (ok, fail))
