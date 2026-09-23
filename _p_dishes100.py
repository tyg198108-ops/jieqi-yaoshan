# -*- coding: utf-8 -*-
"""把资料包《100 道家庭药膳食谱》并入菜谱库。

资料包只给了：菜名 / 主要食材 / 家庭制作 / 搭配定位。
因此：
  - 中医功效、禁忌一律不写（资料没给，不臆造）
  - "搭配定位"属膳食搭配描述，落 nutrition_info，不当作功效
  - 适宜体质与季节由**主要食材已有数据派生**（菜品层面标注 derived_fields），
    否则新菜在引擎里评分恒为 0，永远不会被选中
"""
import json
import os
import re
import math

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'backend', 'data')
PACK = json.load(open(os.path.join(HERE, '_docx_pack.json'), encoding='utf-8'))

SEASON_OF_TERM = {}
for t in json.load(open(os.path.join(DATA, 'solar_terms.json'), encoding='utf-8')):
    SEASON_OF_TERM[t['name']] = t.get('season') or ''

SEASON_WORDS = {'春': '春', '夏': '夏', '秋': '秋', '冬': '冬', '长夏': '夏'}


def season_norm(items):
    """把食材上的季节/节气写法归一到 春夏秋冬"""
    out = set()
    for s in (items or []):
        s = (s or '').strip()
        if not s:
            continue
        if s == '四季':
            out.update(['春', '夏', '秋', '冬'])
            continue
        hit = False
        for k, v in SEASON_WORDS.items():
            if s.startswith(k):
                out.add(v)
                hit = True
                break
        if not hit and s in SEASON_OF_TERM:
            out.add(SEASON_OF_TERM[s])
    return out


TYPE_RULES = [
    (r'凉拌|拌菜|沙拉', '冷碟', '家常凉菜'),
    (r'粥$', '主食', '养生粥品'),
    (r'羹$|糊$|露$|冻$', '甜品', '养生羹品'),
    (r'汤$', '汤品', '家常汤品'),
    (r'蒸', '热菜', '蒸制菜'),
    (r'炖|焖|烧|煲', '热菜', '炖烧菜'),
    (r'炒', '素菜', '家常小炒'),
]
DEFAULT_TYPE = ('热菜', '家常菜')

METHOD_BY_TYPE = {
    '主食': '煮', '甜品': '炖', '汤品': '煮', '冷碟': '凉拌',
    '热菜': '蒸', '素菜': '炒',
}


def guess_type(name, method):
    for pat, dtype, cat in TYPE_RULES:
        if re.search(pat, name):
            return dtype, cat
    if '蒸' in (method or ''):
        return '热菜', '蒸制菜'
    return DEFAULT_TYPE


def split_ingredients(text):
    out = []
    for part in re.split(r'[、,，/]', text or ''):
        part = part.strip()
        if not part:
            continue
        part = re.sub(r'（.*?）|\(.*?\)', '', part).strip()
        if part and part != '清水':
            out.append(part)
    return out


def split_steps(text):
    text = (text or '').strip().rstrip('。')
    if not text:
        return []
    parts = [p.strip() for p in re.split(r'[。；;]', text) if p.strip()]
    return parts


def main():
    ing = json.load(open(os.path.join(DATA, 'ingredients.json'), encoding='utf-8'))
    ing_by_name = {i['name']: i for i in ing}
    alias_index = {}
    for i in ing:
        for a in [x for x in (i.get('alias') or '').split('、') if x]:
            alias_index.setdefault(a, i)

    def lookup(name):
        return ing_by_name.get(name) or alias_index.get(name)

    dishes = json.load(open(os.path.join(DATA, 'dishes.json'), encoding='utf-8'))
    exist_names = {d['name'] for d in dishes}
    next_id = max((d.get('id') or 0) for d in dishes) + 1

    added, skipped, unmatched = [], [], []
    for p in PACK['dishes']:
        name = p['name'].strip()
        if name in exist_names:
            skipped.append(name)
            continue

        parts = split_ingredients(p['ingredients'])
        dtype, category = guess_type(name, p.get('method'))

        # 从主要食材已有数据派生适宜体质与季节
        const_votes, season_votes = {}, {}
        matched_parts = []
        for nm in parts:
            item = lookup(nm)
            if not item:
                unmatched.append((name, nm))
                continue
            matched_parts.append(item['name'])
            for c in (item.get('suitable_constitutions') or []):
                const_votes[c] = const_votes.get(c, 0) + 1
            for s in season_norm(item.get('suitable_seasons')):
                season_votes[s] = season_votes.get(s, 0) + 1

        n = max(1, len(matched_parts))
        need = max(1, math.ceil(n / 2.0))
        consts = sorted([c for c, v in const_votes.items() if v >= need])
        if not consts:
            consts = [c for c, _ in sorted(const_votes.items(),
                                           key=lambda x: -x[1])[:2]]
        seasons = sorted([s for s, v in season_votes.items() if v >= need])
        if not seasons:
            seasons = [s for s, _ in sorted(season_votes.items(),
                                            key=lambda x: -x[1])[:2]]

        dish = {
            'id': next_id,
            'name': name,
            'category': category,
            'dish_type': dtype,
            'main_ingredients': [{'name': nm, 'amount': '适量'} for nm in (matched_parts or parts)],
            'auxiliary_ingredients': [],
            'medicinal_ingredients': [nm for nm in matched_parts
                                      if (lookup(nm) or {}).get('is_medicinal')],
            'cooking_method': METHOD_BY_TYPE.get(dtype, '煮'),
            'cooking_steps': split_steps(p.get('method')),
            'skills': None,
            'efficacy_chinese': None,
            'nutrition_info': (p.get('position') or '').strip() or None,
            'suitable_constitutions': consts,
            'suitable_seasons': [s + '季' for s in seasons],
            'contraindication': None,
            'description': '资料包《100 道家庭药膳食谱》家庭食养菜谱，非疾病食疗方案。',
            'source_lesson': None,
            'source': '引流资料包 V1.0 第四部分',
            'derived_fields': ['suitable_constitutions', 'suitable_seasons'],
            'derived_from': '由主要食材在库数据聚合推导，非课件原文',
        }
        dishes.append(dish)
        exist_names.add(name)
        added.append(name)
        next_id += 1

    json.dump(dishes, open(os.path.join(DATA, 'dishes.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    print('原菜品        :', len(dishes) - len(added))
    print('新增          :', len(added))
    print('重名跳过      :', len(skipped), skipped[:8])
    print('合计          :', len(dishes))
    print('食材未匹配(菜,料):', len(unmatched), unmatched[:10])
    from collections import Counter
    print('新增类型分布  :', Counter(d['dish_type'] for d in dishes[-len(added):]) if added else '无')


if __name__ == '__main__':
    main()
