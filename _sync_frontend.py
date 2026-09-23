# -*- coding: utf-8 -*-
"""
把 backend/data/*.json 同步为前端 app-data.js，保证前后端数据同源。
运行： python _sync_frontend.py
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'backend', 'data')
OUT = os.path.join(ROOT, 'app-data.js')


def load(name):
    with open(os.path.join(DATA, name), 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parts = [
        ('SOLAR_TERMS', load('solar_terms.json')),
        ('CONSTITUTIONS', load('constitutions.json')),
        ('QUESTIONS', load('constitution_questions.json')),
        ('INGREDIENTS', load('ingredients.json')),
        ('DISHES', load('dishes.json')),
        ('RULES', load('rules.json')),
    ]
    buf = []
    for var, obj in parts:
        # 必须挂到 window：顶层 const 只进脚本的词法环境，window.X 取不到，
        # api.js 的 fromLocal() 会误判「本地副本不可用」→ 后端一挂就整页白屏。
        buf.append(f'window.{var} = {json.dumps(obj, ensure_ascii=False)};')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(buf) + '\n')

    size = os.path.getsize(OUT)
    print(f'已生成 {os.path.basename(OUT)}（{size:,} 字节）')
    for var, obj in parts:
        n = len(obj) if isinstance(obj, list) else 'dict'
        print(f'  {var:15s} {n}')


if __name__ == '__main__':
    main()
