# -*- coding: utf-8 -*-
"""补齐菜谱里用到、但库里没有的常见食材（普通食品，不在食药物质目录内）。
性味只在资料包第五部分有记载时才填，其余留空，不臆造。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'backend', 'data')
PACK = json.load(open(os.path.join(HERE, '_docx_pack.json'), encoding='utf-8'))
PACK_NATURE = {p['name']: p for p in PACK['ingredients']}

# （名称, 别名, 分类, 是否按药用管理）
COMMON = [
    ('鸡蛋', '', '优质蛋白类', 0),
    ('番茄', '西红柿', '蔬果类', 0),
    ('洋葱', '', '蔬菜类', 0),
    ('豆腐', '', '豆制品类', 0),
    ('丝瓜', '', '蔬菜类', 0),
    ('黑豆', '', '豆类', 0),
    ('黑米', '', '谷物类', 0),
    ('糙米', '', '谷物类', 0),
    ('菠菜', '', '蔬菜类', 0),
    ('牛肉', '', '畜禽类', 0),
    ('香葱', '葱', '调味类', 0),
    ('紫菜', '', '藻类', 0),
    ('鳜鱼', '桂鱼', '水产类', 0),
    ('彩椒', '', '蔬菜类', 0),
    ('鸡胸肉', '', '禽肉类', 0),
    ('青豆', '豌豆', '豆类', 0),
    ('玉米', '', '谷物类', 0),
    ('虾仁', '虾', '水产类', 0),
    ('西芹', '芹菜', '蔬菜类', 0),
    ('腰果', '', '坚果类', 0),
    ('牛腩', '牛肉', '畜禽类', 0),
    ('苹果', '', '水果类', 0),
    ('燕麦', '', '谷物类', 0),
    ('牛奶', '', '乳品类', 0),
    ('青菜', '', '蔬菜类', 0),
]

# ��谱里的泛称写法 → 库里的具体条目
NORMALIZE = {
    '葱姜': ['葱', '生姜'],
    '鲜百合': ['百合'],
    '牛奶/豆浆': ['牛奶'],
    '鱼块': [],
    '鱼片': [],
}


def main():
    ing = json.load(open(os.path.join(DATA, 'ingredients.json'), encoding='utf-8'))
    names = {i['name'] for i in ing}
    next_id = max((i.get('id') or 0) for i in ing) + 1
    added = []

    for name, alias, cat, is_med in COMMON:
        if name in names:
            continue
        p = PACK_NATURE.get(name) or PACK_NATURE.get(alias)
        nat = (p or {}).get('nature', '').split('/')
        item = {
            'id': next_id,
            'name': name,
            'alias': alias,
            'category': cat,
            'four_natures': (nat[0] or None) if nat else None,
            'five_flavors': [x for x in nat[1]] if len(nat) > 1 and nat[1] else [],
            'meridian_tropism': [],
            'efficacy_chinese': None,
            'nutrition_info': (p or {}).get('nutrition'),
            'suitable_seasons': [],
            'suitable_constitutions': [],
            'contraindication': None,
            'dosage': None,
            'cooking_methods': [x for x in (p or {}).get('cook', '').replace('、', ',').split(',') if x],
            'good_combinations': [x for x in (p or {}).get('pair', '').replace('、', ',').split(',') if x],
            'bad_combinations': [],
            'in_catalog': None,
            'catalog_batch': None,
            'catalog_official': None,
            'catalog_note': '普通食品/食材，不在食药物质目录内，不适用「药食同源」标注',
            'description': None,
            'is_medicinal': is_med,
            'source_lesson': None,
            'source': ('性味与营养特点：资料包 V1.0 第五部分' if p else None),
            'pending_fields': ['four_natures', 'meridian_tropism', 'efficacy_chinese'] if not p else ['meridian_tropism', 'efficacy_chinese'],
        }
        ing.append(item)
        names.add(name)
        added.append(name)
        next_id += 1

    json.dump(ing, open(os.path.join(DATA, 'ingredients.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    # 菜谱里的泛称写法规范化
    dishes = json.load(open(os.path.join(DATA, 'dishes.json'), encoding='utf-8'))
    n = 0
    for d in dishes:
        for key in ('main_ingredients', 'auxiliary_ingredients', 'medicinal_ingredients'):
            src = d.get(key) or []
            out = []
            for it in src:
                nm = it if isinstance(it, str) else it.get('name')
                if nm in NORMALIZE:
                    for new in NORMALIZE[nm]:
                        out.append({'name': new, 'amount': '适量'} if not isinstance(it, str) else new)
                    n += 1
                else:
                    out.append(it)
            d[key] = out
    json.dump(dishes, open(os.path.join(DATA, 'dishes.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    print('新增常见食材  :', len(added), added)
    print('泛称规范化    :', n, '处')
    print('食材总数      :', len(ing))


if __name__ == '__main__':
    main()
