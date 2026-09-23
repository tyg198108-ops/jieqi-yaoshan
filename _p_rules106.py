# -*- coding: utf-8 -*-
"""2024 年新增 4 种食药物质（地黄、麦冬、天冬、化橘红）的官方人群提示。

依据：国家卫健委 2024 年第 4 号公告解读明确——孕妇、哺乳期妇女及婴幼儿等
特殊人群**不推荐食用**这 4 种物质（资料包 V1.0 第六部分第 46 行同款表述）。
级别取 block：官方措辞是"不推荐"，系统侧按红线处理更稳。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'backend', 'data')
PATH = os.path.join(DATA, 'rules.json')

FOUR = ['地黄', '麦冬', '天冬', '化橘红']
GROUPS = ['pregnant', 'lactating', 'children']
SRC = '国家卫健委 2024 年第 4 号公告解读；资料包 V1.0 第六部分'


def main():
    r = json.load(open(PATH, encoding='utf-8'))
    g = r.setdefault('special_group_contraindications', {})

    touched = []
    for key in GROUPS:
        grp = g.get(key)
        if not grp:
            continue
        forbid = grp.setdefault('forbidden_ingredients', [])
        for name in FOUR:
            if name not in forbid:
                forbid.append(name)
        grp['warning'] = (grp.get('warning') or '').rstrip('；') + \
            '；2024 年新增的地黄、麦冬、天冬、化橘红，官方解读提示孕妇、哺乳期妇女及婴幼儿不推荐食用'
        grp.setdefault('source_lesson', '')
        grp['catalog_source'] = SRC
        touched.append(key)

    # 单味提示表也记一笔，A 端看得到出处
    c = r.setdefault('ingredient_cautions', [])
    exist = {x.get('ingredient') for x in c}
    for name in FOUR:
        if name in exist:
            continue
        c.append({
            'ingredient': name,
            'caution_groups': ['孕妇', '哺乳期妇女', '婴幼儿'],
            'reason': '2024 年第 4 号公告解读明确：孕妇、哺乳期妇女及婴幼儿等特殊人群不推荐食用',
            'level': 'block',
            'source_lesson': SRC,
        })

    meta = r.setdefault('_meta', {})
    meta.setdefault('decisions', {})['Q_catalog_106'] = \
        '食材库按卫健委食药物质目录（累计 106 种）校准，2024 年新增 4 种按官方提示加人群红线（2026-09-23）'
    meta['catalog'] = {
        'total': 106,
        'batches': {
            '2002': 87, '2019': 6, '2023': 9, '2024': 4
        },
        'source': SRC,
        'note': '性味归经只在课件/资料包有记载时填写，其余留空并标 pending_fields，不作补写',
    }

    json.dump(r, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('已加人群红线  :', touched)
    print('新增单味提示  :', [x['ingredient'] for x in c if x['ingredient'] in FOUR])
    print('rules.json 键 :', len(r))


if __name__ == '__main__':
    main()
