# -*- coding: utf-8 -*-
"""修复 98 道资料包菜的食材与技法。

上轮 _p_dishes100.py 有两个 bug，导致资料包菜的食材信息几乎全丢：
  1. main_ingredients 只取了「能在食材库查到的食材」(matched_parts)，
     西兰花、虾仁、冬瓜这类没进库的普通食材全被丢掉——
     「西兰花炒虾仁」入库后主料只剩一个「蒜」。
  2. cooking_method 是按 dish_type 硬塞的（素菜一律「炒」、热菜一律「蒸」），
     不是菜谱原文技法。这直接让「烹饪方式多样」这条要求没有数据支撑。

本脚本用 _docx_pack.json（资料包原文）回填：
  - main_ingredients / auxiliary_ingredients：按「主料 / 配料」重分
  - medicinal_ingredients：库内 is_medicinal=1 的食材单独列出
  - cooking_method：从原做法文字里抽真实技法关键词
  - suitable_constitutions / seasons：主料变了，派生结果要跟着重算
只动 source 为资料包的菜，课件菜一个字不改。
"""
import json
import os
import re
import math
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'backend', 'data')
PACK = {p['name'].strip(): p for p in
        json.load(open(os.path.join(HERE, '_docx_pack.json'), encoding='utf-8'))['dishes']}

SEASON_OF_TERM = {}
for t in json.load(open(os.path.join(DATA, 'solar_terms.json'), encoding='utf-8')):
    SEASON_OF_TERM[t['name']] = t.get('season') or ''
SEASON_WORDS = {'春': '春', '夏': '夏', '秋': '秋', '冬': '冬', '长夏': '夏'}

# 配料/调味：不进主料，单独放 auxiliary_ingredients。
# 「葱姜」「姜片」这类连写词一并收进来，否则会被当成主料端上桌。
GARNISH = set('''葱 姜 蒜 葱姜 姜片 葱花 蒜末 蒜片 葱丝 姜丝 香菜 香葱 食用油 油 香油 盐 食盐 醋
白醋 白糖 冰糖 料酒 生抽 老抽 酱油 蚝油 淀粉 水淀粉 胡椒 胡椒粉 花椒 八角 桂皮 香叶
辣椒 干辣椒 孜然 蜂蜜 芥末 蒸鱼豉油 豉油 番茄酱 豆瓣酱 牛奶 豆浆 清水 柠檬 柠檬汁
芝麻油 花椒油 五香粉 高汤 橄榄油 麻油'''.split())

# 技法：按优先级从原做法里抽，命中靠前的优先（一道菜可能又焯又炒，取主技法）
METHOD_PATTERNS = [
    ('焖', r'焖'), ('炖', r'炖|煨'), ('卤', r'卤'), ('蒸', r'蒸'),
    ('煮', r'煮|焯|烫|煲|炖锅'), ('炒', r'炒|爆|煸'), ('煎', r'煎'),
    ('拌', r'拌|腌渍'), ('烤', r'烤|焗'), ('炸', r'炸'),
]


def split_ingredients(text):
    out = []
    for part in re.split(r'[、,，/]', text or ''):
        part = re.sub(r'（.*?）|\(.*?\)', '', part or '').strip()
        part = part.replace('适量', '').strip()
        if part and part != '清水':
            out.append(part)
    return out


def season_norm(items):
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


def pick_method(method_text, dish_name, old):
    """菜名里的技法字最准（「西兰花炒虾仁」菜名带炒，
    但做法是「虾仁焯熟…翻炒」，只扫做法会被「焯」带偏成煮），
    菜名没写才回退到做法原文。"""
    for source in (dish_name, method_text):
        if not source:
            continue
        for m, pat in METHOD_PATTERNS:
            if re.search(pat, source):
                return m
    return old or '煮'


def main():
    ing = json.load(open(os.path.join(DATA, 'ingredients.json'), encoding='utf-8'))
    by_name = {i['name']: i for i in ing}
    alias = {}
    for i in ing:
        for a in [x for x in (i.get('alias') or '').split('、') if x]:
            alias.setdefault(a, i)

    def lookup(name):
        return by_name.get(name) or alias.get(name)

    dishes = json.load(open(os.path.join(DATA, 'dishes.json'), encoding='utf-8'))
    fixed, missed, stats_main_before, stats_main_after = [], [], 0, 0

    for d in dishes:
        if '引流资料包' not in (d.get('source') or ''):
            continue
        p = PACK.get(d['name'])
        if not p:
            missed.append(d['name'])
            continue

        parts = split_ingredients(p.get('ingredients'))
        mains, auxs, meds = [], [], []
        const_votes, season_votes = {}, {}

        for nm in parts:
            item = lookup(nm)
            # 药材只认「药食同源目录内」(in_catalog=1)。
            # 用 is_medicinal 会把冬瓜、绿豆、苦瓜这些家常食材也算成药，
            # 一道「冬瓜虾仁」就成药膳了，席单上全是药。
            if item and item.get('in_catalog') == 1 and nm not in GARNISH:
                meds.append({'name': item['name'], 'amount': None})
            elif nm in GARNISH or re.search(r'盐$|糖$|油$|醋$|酱$|酒$', nm):
                auxs.append({'name': nm, 'amount': None})
            else:
                mains.append({'name': nm, 'amount': None})
            if item:
                for c in (item.get('suitable_constitutions') or []):
                    const_votes[c] = const_votes.get(c, 0) + 1
                for s in season_norm(item.get('suitable_seasons')):
                    season_votes[s] = season_votes.get(s, 0) + 1

        before = [x.get('name') if isinstance(x, dict) else x for x in (d.get('main_ingredients') or [])]
        stats_main_before += len(before)
        stats_main_after += len(mains)

        d['main_ingredients'] = mains or [{'name': nm, 'amount': None} for nm in parts]
        d['auxiliary_ingredients'] = auxs
        d['medicinal_ingredients'] = meds
        d['cooking_method'] = pick_method(p.get('method'), d['name'], d.get('cooking_method'))

        # 主料变了，适宜体质/季节是派生字段，必须跟着重算，标 derived_fields 保持可追溯
        n = max(1, len(parts))
        need = max(1, math.ceil(n / 2.0))
        consts = sorted([c for c, v in const_votes.items() if v >= need]) or \
            [c for c, _ in sorted(const_votes.items(), key=lambda x: -x[1])[:2]]
        seasons = sorted([s for s, v in season_votes.items() if v >= need]) or \
            [s for s, _ in sorted(season_votes.items(), key=lambda x: -x[1])[:2]]
        d['suitable_constitutions'] = consts
        d['suitable_seasons'] = [s + '季' for s in seasons]
        d['derived_fields'] = ['suitable_constitutions', 'suitable_seasons']
        d['derived_from'] = '由主要食材在库数据聚合推导，非课件原文'
        fixed.append(d['name'])

    json.dump(dishes, open(os.path.join(DATA, 'dishes.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    print('修复菜品      :', len(fixed))
    print('未找到原文    :', len(missed), missed[:5])
    print('主料条目数    : %d → %d' % (stats_main_before, stats_main_after))
    print('技法分布(资料包菜):',
          Counter(d['cooking_method'] for d in dishes if '引流资料包' in (d.get('source') or '')))


if __name__ == '__main__':
    main()
