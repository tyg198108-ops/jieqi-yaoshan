# -*- coding: utf-8 -*-
"""
节气药膳师 · 数据清洗脚本（第1步）
1) 菜品去重（41 -> 35），保留字段最完整的一条，重排 id
2) 食材命名统一（别名归一）
3) 食材库补录：台账有据的药材补性味归经；台账无据的标为普通食材/调味品，性味留空待补
运行： python _clean_data.py    （会自动备份为 .bak）
"""
import json, os, shutil, glob
from collections import defaultdict

DATA = os.path.join(os.path.dirname(__file__), 'backend', 'data')


def load(name):
    with open(os.path.join(DATA, name), 'r', encoding='utf-8') as f:
        return json.load(f)


def save(name, obj):
    p = os.path.join(DATA, name)
    if not os.path.exists(p + '.bak'):
        shutil.copy2(p, p + '.bak')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print('  写入', name)


# ---------------- 1. 菜品去重 ----------------
def clean_dishes(dishes):
    # 归一化：补齐所有出现过的字段
    all_keys = []
    for d in dishes:
        for k in d.keys():
            if k not in all_keys:
                all_keys.append(k)
    for d in dishes:
        for k in all_keys:
            d.setdefault(k, None)

    def richness(d):
        """字段有值数量 + 节气/体质细化程度，越高越优先保留"""
        filled = sum(1 for v in d.values() if v not in (None, '', [], {}))
        seasons = len(d.get('suitable_seasons') or [])
        consts = len(d.get('suitable_constitutions') or [])
        steps = len(d.get('cooking_steps') or [])
        return (filled, seasons, consts, steps)

    groups = defaultdict(list)
    for d in dishes:
        groups[d['name']].append(d)

    kept, removed = [], []
    for name, items in groups.items():
        items.sort(key=richness, reverse=True)
        kept.append(items[0])
        for x in items[1:]:
            removed.append((name, x.get('id')))

    # 保持原始顺序（按第一次出现的名字顺序）
    order = []
    for d in dishes:
        if d['name'] not in order:
            order.append(d['name'])
    kept.sort(key=lambda d: order.index(d['name']))

    for i, d in enumerate(kept, 1):
        d['id'] = i
    return kept, removed, all_keys


# ---------------- 2. 命名统一 ----------------
ALIAS = {
    '枸杞': '枸杞子',
    '核桃仁': '核桃',
    '老鸭': '鸭肉',
    '鲜百合': '百合',
    '木耳': '黑木耳',
    '干荷叶': '荷叶',
    '鲜荷叶': '荷叶',
    '雪梨': '梨',
    '小米/糙米': '小米',
}


def norm(name):
    return ALIAS.get(name, name)


def apply_alias(dishes):
    changed = defaultdict(int)
    for d in dishes:
        for field in ('main_ingredients', 'medicinal_ingredients', 'auxiliary_ingredients'):
            for item in (d.get(field) or []):
                old = item.get('name')
                new = norm(old)
                if new != old:
                    changed[f'{old} -> {new}'] += 1
                    item['name'] = new
    return changed


# ---------------- 3. 食材库补录 ----------------
# 台账有据（来自 _知识台账/中医药膳营养师_知识点台账.md），带 source_lesson
NEW_MEDICINAL = [
    dict(name='石斛', category='滋阴类', four_natures='微寒', five_flavors=['甘'],
         meridian_tropism=['胃', '肾'], efficacy_chinese='益胃生津、滋阴清热',
         contraindication='阳虚怕冷者不宜', dosage='课件未给出统一剂量',
         suitable_constitutions=['阴虚质', '湿热质'], suitable_seasons=['秋季', '夏季'],
         cooking_methods=['炖', '煮'], in_catalog=1, is_medicinal=1,
         source_lesson='第05课 P13', description='滋阴清热，代表膳：石斛老鸭汤'),
    dict(name='荷叶', category='祛湿类', four_natures='平', five_flavors=['苦', '涩'],
         meridian_tropism=['肝', '脾', '胃'], efficacy_chinese='清暑化湿、升发清阳',
         contraindication='课件未涉及', dosage='课件未给出统一剂量',
         suitable_constitutions=['痰湿质', '湿热质'], suitable_seasons=['夏季'],
         cooking_methods=['蒸', '煮', '泡'], in_catalog=1, is_medicinal=1,
         source_lesson='第06课 P10', description='清暑化湿，代表膳：荷叶山楂饮'),
    dict(name='冬瓜', category='祛湿类', four_natures='凉', five_flavors=['甘', '淡'],
         meridian_tropism=['肺', '大肠', '小肠', '膀胱'], efficacy_chinese='清热利水、消肿解毒',
         contraindication='课件未涉及', dosage='课件未给出统一剂量',
         suitable_constitutions=['痰湿质', '湿热质'], suitable_seasons=['夏季'],
         cooking_methods=['炖', '煮', '炒'], in_catalog=1, is_medicinal=1,
         source_lesson='第06课 P10', description='清热利水，代表膳：冬瓜排骨汤'),
    dict(name='梨', category='润肺类', four_natures='凉', five_flavors=['甘', '微酸'],
         meridian_tropism=['肺', '胃'], efficacy_chinese='生津润燥、清热化痰',
         contraindication='课件未涉及', dosage='课件未给出统一剂量',
         suitable_constitutions=['阴虚质'], suitable_seasons=['秋季'],
         cooking_methods=['炖', '蒸', '生食'], in_catalog=1, is_medicinal=1,
         source_lesson='第06课 P13', description='生津润燥，适用咽干咳嗽、便秘'),
    dict(name='黑木耳', category='活血类', four_natures='平', five_flavors=['甘'],
         meridian_tropism=['胃', '大肠'], efficacy_chinese='凉血止血、活血润燥',
         contraindication='课件未涉及', dosage='课件未给出统一剂量',
         suitable_constitutions=['血瘀质'], suitable_seasons=['四季'],
         cooking_methods=['炒', '凉拌', '煮'], in_catalog=1, is_medicinal=1,
         source_lesson='第06课 P6', description='活血润燥，代表膳：黑木耳红枣汤'),
]

SEASONINGS = {'冰糖', '白糖', '红糖', '生抽', '醋', '白醋', '蒜', '蒜末', '香菜', '蒸肉米粉'}

# 药材功效分类关键词。注意：is_medicinal 与 in_catalog 是两个维度，不可混用。
#   in_catalog  = 是否在国家药食同源目录（法律属性，决定能否经营）
#   is_medicinal= 是否按药材对待（风控属性，决定是否参与配伍/剂量/人群校验）
# 黄芪、人参、当归即使目录归属待核，也必须参与校验，否则会漏掉"人参恶萝卜""当归忌孕妇"等红线。
MED_CATS = ('补气', '补血', '滋阴', '壮阳', '温阳', '补阳', '补阴', '理气', '活血', '清热',
            '祛湿', '安神', '健脾', '润肺', '解表', '温里', '消食', '涩精', '化痰', '补肺',
            '润肠', '补肝')

# in_catalog 存疑、需胡老师按台账 Q1（药食同源目录版本）核定的条目
CATALOG_AUDIT = {
    '黄芪': '原数据 in_catalog=0，但属药食同源常见药材，目录归属待核（台账 Q1）',
    '当归': '原数据 in_catalog=0，但属药食同源常见药材，目录归属待核（台账 Q1）',
    '人参': '人工种植人参属试点管理品种，非目录常驻，使用限量需核定（台账 Q1）',
}


def build_ingredients(ingredients, dishes):
    names = {x['name'] for x in ingredients}
    used = set()
    for d in dishes:
        for field in ('main_ingredients', 'medicinal_ingredients', 'auxiliary_ingredients'):
            for item in (d.get(field) or []):
                used.add(item['name'])

    missing = sorted(used - names)
    print(f'  菜品引用但食材库未收录：{len(missing)} 种')

    # 3a) 台账有据的药材
    added_med = []
    for item in NEW_MEDICINAL:
        if item['name'] not in names:
            ingredients.append(item)
            added_med.append(item['name'])
    names |= set(added_med)

    # 3b) 台账无据的 -> 普通食材/调味品，性味归经留空，标 source='pending'
    added_common = []
    for nm in missing:
        if nm in names:
            continue
        cat = '调味品' if nm in SEASONINGS else '普通食材'
        ingredients.append(dict(
            name=nm, category=cat, four_natures=None, five_flavors=None,
            meridian_tropism=None, efficacy_chinese=None, nutrition_info=None,
            suitable_seasons=None, suitable_constitutions=None,
            contraindication=None, dosage=None, cooking_methods=None,
            good_combinations=None, bad_combinations=None,
            in_catalog=0, is_medicinal=0,
            source_lesson=None, source='pending',
            description='课件未涉及该食材的性味归经，待补充（目前仅参与采购清单，不参与配伍校验）',
        ))
        added_common.append(nm)

    # 3c) 老条目补齐新字段（is_medicinal 按功效分类强制重算，不受 in_catalog 影响）
    for x in ingredients:
        x['is_medicinal'] = 1 if any(c in (x.get('category') or '') for c in MED_CATS) else 0
        x.setdefault('source_lesson', None)
        x.setdefault('source', 'course' if x.get('source_lesson') else 'legacy')
        if x['name'] in CATALOG_AUDIT:
            x['catalog_note'] = CATALOG_AUDIT[x['name']]
        else:
            x.setdefault('catalog_note', None)
        for k in ('alias', 'nutrition_info', 'dosage', 'cooking_methods',
                  'good_combinations', 'bad_combinations', 'in_catalog', 'description'):
            x.setdefault(k, None)

    for i, x in enumerate(ingredients, 1):
        x['id'] = i
    return added_med, added_common, missing


def main():
    print('=' * 60)
    print('1) 菜品去重')
    dishes = load('dishes.json')
    kept, removed, keys = clean_dishes(dishes)
    print(f'  原始 {len(dishes)} 道 -> 去重后 {len(kept)} 道')
    for name, oid in removed:
        print(f'    移除重复：{name}（旧 id={oid}）')

    print('2) 命名统一')
    changed = apply_alias(kept)
    for k, v in changed.items():
        print(f'    {k}   x{v}')

    print('3) 食材库补录')
    ingredients = load('ingredients.json')
    added_med, added_common, missing = build_ingredients(ingredients, kept)
    print(f'  补录药材（台账有据）：{len(added_med)} -> {"、".join(added_med)}')
    print(f'  补录普通食材/调味品（性味待补）：{len(added_common)} 种')

    save('dishes.json', kept)
    save('ingredients.json', ingredients)

    print('=' * 60)
    print(f'菜品 {len(kept)} 道 | 食材 {len(ingredients)} 味'
          f'（药用 {sum(1 for x in ingredients if x.get("is_medicinal"))} / '
          f'普通 {sum(1 for x in ingredients if not x.get("is_medicinal"))}）')


if __name__ == '__main__':
    main()
