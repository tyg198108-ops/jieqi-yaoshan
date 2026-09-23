# -*- coding: utf-8 -*-
"""金陵老味道菜单冷碟入库（胡老师 2026-09-23 提供菜单图片）。

原则（与资料包导入一致）：
- 菜品只录菜单可见信息：菜名、主辅料（菜单常识可判）、技法（菜名可判）；
  功效/禁忌菜单未写，一律置 null 并标 pending_fields，不编造。
- 食材性味归经功效留空 pending，只标类别与目录归属。
- 口味(flavor)、适宜体质/季节不派生，如实留空。
"""
import json, shutil, sys

DISHES = 'backend/data/dishes.json'
INGS = 'backend/data/ingredients.json'
SRC = '金陵老味道菜单（胡老师 2026-09-23 提供）'

shutil.copy(DISHES, DISHES + '.bak.cold')
shutil.copy(INGS, INGS + '.bak.cold')

ings = json.load(open(INGS, encoding='utf-8'))
dishes = json.load(open(DISHES, encoding='utf-8'))

# ---------------- 新增食材 ----------------
# (name, alias, category, catalog_note)
NEW_INGS = [
    ('鹅肉',   '', '畜禽类', '普通食品食材，不在食药物质目录内'),
    ('鸭胗',   '鸭肫', '畜禽类', '普通食品食材（内脏），不在食药物质目录内'),
    ('鸭头',   '', '畜禽类', '普通食品食材，不在食药物质目录内'),
    ('猪肉皮', '肉皮', '畜禽类', '普通食品食材，不在食药物质目录内'),
    ('猪肉',   '', '畜禽类', '普通食品食材，不在食药物质目录内'),
    ('猪头肉', '', '畜禽类', '普通食品食材，不在食药物质目录内'),
    ('猪口条', '口条、猪舌', '畜禽类', '普通食品食材（内脏），不在食药物质目录内'),
    ('鸡爪',   '凤爪', '畜禽类', '普通食品食材，不在食药物质目录内'),
    ('花生',   '花生米', '坚果油脂类', '普通食品食材，不在食药物质目录内'),
    ('皮蛋',   '松花蛋', '蛋类', '普通食品食材（蛋制品），不在食药物质目录内'),
    ('黄参',   '', '其他类', '甘肃山丹地方特色食材（山丹黄参），是否属食药物质待确认，未入 106 目录'),
    ('柠檬',   '', '果蔬类', '普通食品食材，不在食药物质目录内'),
]
exist = {i['name'] for i in ings}
nid = max(i['id'] for i in ings) + 1
for name, alias, cat, note in NEW_INGS:
    if name in exist:
        print('食材已存在，跳过:', name); continue
    ings.append({
        'id': nid, 'name': name, 'alias': alias, 'category': cat,
        'four_natures': None, 'five_flavors': [], 'meridian_tropism': [],
        'efficacy_chinese': None, 'nutrition_info': None,
        'suitable_seasons': [], 'suitable_constitutions': [],
        'contraindication': None, 'dosage': None, 'cooking_methods': [],
        'good_combinations': [], 'bad_combinations': [],
        'in_catalog': None, 'catalog_batch': None, 'catalog_official': None,
        'catalog_note': note, 'description': None,
        'is_medicinal': 0, 'source_lesson': None, 'source': SRC,
        'pending_fields': ['four_natures', 'five_flavors', 'efficacy_chinese', 'contraindication'],
    })
    nid += 1
    print('新增食材:', name, '(', cat, ')')

# ---------------- 新增菜品 ----------------
# (name, main[], aux[], med[], method)
NEW_DISHES = [
    # ---- 冷荤 13 ----
    ('石斛牛肉',   ['牛肉'], [], ['石斛'], '卤'),
    ('盐水鹅',     ['鹅肉'], [], [], '卤'),
    ('金陵盐水鸭', ['鸭肉'], [], [], '卤'),
    ('白斩鸡',     ['鸡肉'], ['姜', '葱'], [], '煮'),
    ('柠檬凤爪',   ['鸡爪'], ['柠檬'], [], '腌'),
    ('水晶肴肉',   ['猪肉', '猪肉皮'], ['姜'], [], '冻'),
    ('盐水鸭胗',   ['鸭胗'], [], [], '卤'),
    ('五香牛肉',   ['牛肉'], [], [], '卤'),
    ('六合猪头肉', ['猪头肉'], [], [], '卤'),
    ('卤水口条',   ['猪口条'], [], [], '卤'),
    ('层层脆',     ['牛肉'], [], [], '卤'),
    ('麻辣鸭肫',   ['鸭胗'], ['辣椒', '花椒'], [], '卤'),
    ('麻辣鸭头',   ['鸭头'], ['辣椒', '花椒'], [], '卤'),
    # ---- 冷素 8 ----
    ('养生菊苣',     ['菊苣'], [], [], '拌'),
    ('山丹黄参',     ['黄参'], [], [], None),
    ('老南京酱黄瓜', ['黄瓜'], [], [], '腌'),
    ('桂花蜜汁天麻', ['天麻'], ['桂花', '蜂蜜'], [], '蒸'),
    ('椒盐花生米',   ['花生'], [], [], '炸'),
    ('剁椒皮蛋',     ['皮蛋'], ['辣椒'], [], '拌'),
    ('橘汁萝卜皮',   ['白萝卜'], ['橙汁', '白糖', '白醋'], [], '腌'),
    ('紫气东来',     ['皮蛋', '嫩豆腐'], [], [], '蒸'),
]
exist_d = {d['name'] for d in dishes}
did = max(d['id'] for d in dishes) + 1
for name, main, aux, med, method in NEW_DISHES:
    if name in exist_d:
        print('菜品已存在，跳过:', name); continue
    dishes.append({
        'id': did, 'name': name,
        'category': '金陵老味道冷碟',
        'dish_type': '冷碟',
        'main_ingredients': [{'name': n, 'amount': None} for n in main],
        'auxiliary_ingredients': [{'name': n, 'amount': None} for n in aux],
        'medicinal_ingredients': [{'name': n, 'amount': None} for n in med],
        'cooking_method': method, 'cooking_steps': [], 'skills': None,
        'efficacy_chinese': None, 'nutrition_info': None,
        'suitable_constitutions': [], 'suitable_seasons': [],
        'contraindication': None,
        'description': '金陵老味道菜单冷碟，菜单菜品；功效禁忌菜单未载，待补。',
        'source_lesson': None, 'source': SRC,
        'derived_fields': [], 'derived_from': None, 'flavor': None,
        'pending_fields': ['efficacy_chinese', 'flavor'],
    })
    did += 1
    print('新增菜品: %-8s %s' % (name, ('药膳配伍:' + '、'.join(med)) if med else ''))

json.dump(ings, open(INGS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(dishes, open(DISHES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('--- 完成: 食材 %d, 菜品 %d ---' % (len(ings), len(dishes)))
