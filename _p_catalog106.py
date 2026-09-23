# -*- coding: utf-8 -*-
"""按国家卫健委食药物质目录（累计 106 种）校准食材库。

来源（四批次，均为国家卫健委/原卫生部公告）：
  2002 年 87 种 —— 卫法监发〔2002〕51 号
  2019 年  6 种 —— 2019 年第 8 号公告（当归、山柰、西红花、草果、姜黄、荜茇）
  2023 年  9 种 —— 2023 年第 9 号公告（党参、肉苁蓉(荒漠)、铁皮石斛、西洋参、黄芪、灵芝、山茱萸、天麻、杜仲叶）
  2024 年  4 种 —— 2024 年第 4 号公告（地黄、麦冬、天冬、化橘红）

原则：只录入有公告依据的事实字段。性味归经、功效等中医内容，
      仅在课件或资料包有记载时才填，否则留空并写进 pending_fields，不臆造。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'backend', 'data')
PACK = json.load(open(os.path.join(HERE, '_docx_pack.json'), encoding='utf-8'))

BATCH = {
    '2002': '2002 年首批 87 种（卫法监发〔2002〕51 号）',
    '2019': '2019 年第 8 号公告新增 6 种',
    '2023': '2023 年第 9 号公告新增 9 种',
    '2024': '2024 年第 4 号公告新增 4 种',
}

# （通用名, 目录官方名, 批次, 别名, 中药学常规分类）
CATALOG = [
    # ---------- 2002 年首批 87 种 ----------
    ('丁香', '丁香', '2002', '公丁香', '温里类、理气类'),
    ('八角茴香', '八角茴香', '2002', '大料、八角', '温里类、调味类'),
    ('刀豆', '刀豆', '2002', '', '理气类'),
    ('小茴香', '小茴香', '2002', '茴香', '温里类、理气类'),
    ('小蓟', '小蓟', '2002', '刺儿菜', '清热类、止血类'),
    ('山药', '山药', '2002', '淮山、薯蓣', '补气类、养阴类'),
    ('山楂', '山楂', '2002', '山里红', '消食类、活血类'),
    ('马齿苋', '马齿苋', '2002', '马齿菜', '清热类'),
    ('乌梢蛇', '乌梢蛇', '2002', '', '祛风湿类'),
    ('乌梅', '乌梅', '2002', '酸梅', '收涩类、生津类'),
    ('木瓜', '木瓜', '2002', '宣木瓜', '祛风湿类、消食类'),
    ('火麻仁', '火麻仁', '2002', '麻子仁', '润下类'),
    ('代代花', '代代花', '2002', '玳玳花', '理气类'),
    ('玉竹', '玉竹', '2002', '葳蕤', '养阴类'),
    ('甘草', '甘草', '2002', '国老', '补气类、调和类'),
    ('白芷', '白芷', '2002', '', '解表类'),
    ('白果', '白果', '2002', '银杏果', '收涩类、平喘类'),
    ('白扁豆', '白扁豆', '2002', '扁豆', '补气类、化湿类'),
    ('白扁豆花', '白扁豆花', '2002', '', '化湿类'),
    ('龙眼肉', '龙眼肉（桂圆）', '2002', '桂圆、桂圆肉', '补血类、安神类'),
    ('决明子', '决明子', '2002', '', '清热类、平肝类'),
    ('百合', '百合', '2002', '', '养阴类、安神类'),
    ('肉豆蔻', '肉豆蔻', '2002', '', '收涩类、温里类'),
    ('肉桂', '肉桂', '2002', '桂皮', '温里类'),
    ('余甘子', '余甘子', '2002', '油甘子', '清热类、生津类'),
    ('佛手', '佛手', '2002', '佛手柑', '理气类'),
    ('杏仁', '杏仁（甜、苦）', '2002', '苦杏仁、甜杏仁', '化痰止咳类'),
    ('沙棘', '沙棘', '2002', '', '活血类、消食类'),
    ('牡蛎', '牡蛎', '2002', '生蚝', '平肝类、养阴类'),
    ('芡实', '芡实', '2002', '鸡头米', '收涩类、补脾类'),
    ('花椒', '花椒', '2002', '', '温里类'),
    ('赤小豆', '赤小豆', '2002', '红小豆', '利水类'),
    ('阿胶', '阿胶', '2002', '', '补血类'),
    ('鸡内金', '鸡内金', '2002', '', '消食类'),
    ('麦芽', '麦芽', '2002', '', '消食类、回乳类'),
    ('昆布', '昆布', '2002', '海带', '化痰类、利水类'),
    ('枣', '枣（大枣、酸枣、黑枣）', '2002', '大枣、红枣、黑枣', '补气类、养血类'),
    ('罗汉果', '罗汉果', '2002', '', '清热类、利咽类'),
    ('郁李仁', '郁李仁', '2002', '', '润下类'),
    ('金银花', '金银花', '2002', '双花、忍冬花', '清热类'),
    ('青果', '青果', '2002', '橄榄', '清热类、利咽类'),
    ('鱼腥草', '鱼腥草', '2002', '折耳根', '清热类'),
    ('姜', '姜（生姜、干姜）', '2002', '生姜、干姜', '解表类、温里类'),
    ('枳椇子', '枳椇子', '2002', '拐枣', '解酒类、生津类'),
    ('枸杞子', '枸杞子', '2002', '枸杞', '养阴类、补肝肾类'),
    ('栀子', '栀子', '2002', '山栀子', '清热类'),
    ('砂仁', '砂仁', '2002', '', '化湿类、理气类'),
    ('胖大海', '胖大海', '2002', '', '清热类、利咽类'),
    ('茯苓', '茯苓', '2002', '云苓', '利水类、健脾类'),
    ('香橼', '香橼', '2002', '', '理气类'),
    ('香薷', '香薷', '2002', '', '解表类、化湿类'),
    ('桃仁', '桃仁', '2002', '', '活血类、润下类'),
    ('桑叶', '桑叶', '2002', '', '清热类、解表类'),
    ('桑椹', '桑椹', '2002', '桑葚', '养阴类、补血类'),
    ('桔红', '桔红', '2002', '', '化痰类、理气类'),
    ('桔梗', '桔梗', '2002', '', '化痰类、利咽类'),
    ('益智仁', '益智仁', '2002', '', '温里类、收涩类'),
    ('荷叶', '荷叶', '2002', '', '清热类、利湿类'),
    ('莱菔子', '莱菔子', '2002', '萝卜子', '消食类、化痰类'),
    ('莲子', '莲子', '2002', '莲肉', '收涩类、补脾类'),
    ('高良姜', '高良姜', '2002', '', '温里类'),
    ('淡竹叶', '淡竹叶', '2002', '', '清热类'),
    ('淡豆豉', '淡豆豉', '2002', '', '解表类'),
    ('菊花', '菊花', '2002', '', '清热类、平肝类'),
    ('菊苣', '菊苣', '2002', '', '清热类'),
    ('黄芥子', '黄芥子', '2002', '芥菜子', '化痰类'),
    ('黄精', '黄精', '2002', '', '养阴类、补气类'),
    ('紫苏', '紫苏', '2002', '苏叶', '解表类、理气类'),
    ('紫苏籽', '紫苏籽', '2002', '苏子', '化痰类、润下类'),
    ('葛根', '葛根', '2002', '', '解表类、生津类'),
    ('黑芝麻', '黑芝麻', '2002', '芝麻', '养阴类、补肝肾类'),
    ('黑胡椒', '黑胡椒', '2002', '胡椒', '温里类'),
    ('槐米', '槐米', '2002', '', '清热类、止血类'),
    ('槐花', '槐花', '2002', '', '清热类、止血类'),
    ('蒲公英', '蒲公英', '2002', '婆婆丁', '清热类'),
    ('蜂蜜', '蜂蜜', '2002', '', '补气类、润燥类'),
    ('榧子', '榧子', '2002', '香榧', '驱虫类'),
    ('酸枣仁', '酸枣仁', '2002', '', '安神类'),
    ('鲜白茅根', '鲜白茅根', '2002', '白茅根', '清热类、止血类'),
    ('鲜芦根', '鲜芦根', '2002', '芦根', '清热类、生津类'),
    ('蝮蛇', '蝮蛇', '2002', '', '祛风湿类'),
    ('橘皮', '橘皮', '2002', '陈皮', '理气类、化痰类'),
    ('薄荷', '薄荷', '2002', '', '解表类、清热类'),
    ('薏苡仁', '薏苡仁', '2002', '薏米、苡仁', '利水类、健脾类'),
    ('薤白', '薤白', '2002', '野蒜', '理气类、通阳类'),
    ('覆盆子', '覆盆子', '2002', '', '收涩类、补肝肾类'),
    ('藿香', '藿香', '2002', '', '化湿类、解表类'),
    # ---------- 2019 年新增 6 种 ----------
    ('当归', '当归', '2019', '', '补血类、活血类'),
    ('山柰', '山柰', '2019', '沙姜', '温里类、调味类'),
    ('西红花', '西红花', '2019', '藏红花、番红花', '活血类'),
    ('草果', '草果', '2019', '', '化湿类、调味类'),
    ('姜黄', '姜黄', '2019', '', '活血类、调味类'),
    ('荜茇', '荜茇', '2019', '', '温里类、调味类'),
    # ---------- 2023 年新增 9 种 ----------
    ('党参', '党参', '2023', '', '补气类'),
    ('肉苁蓉', '肉苁蓉（荒漠）', '2023', '', '补阳类、润下类'),
    ('铁皮石斛', '铁皮石斛', '2023', '石斛', '养阴类'),
    ('西洋参', '西洋参', '2023', '花旗参', '补气类、养阴类'),
    ('黄芪', '黄芪', '2023', '', '补气类'),
    ('灵芝', '灵芝', '2023', '', '安神类、补气类'),
    ('山茱萸', '山茱萸', '2023', '山萸肉', '收涩类、补肝肾类'),
    ('天麻', '天麻', '2023', '', '平肝类、息风类'),
    ('杜仲叶', '杜仲叶', '2023', '', '补阳类'),
    # ---------- 2024 年新增 4 种 ----------
    ('地黄', '地黄', '2024', '', '清热类、养阴类'),
    ('麦冬', '麦冬', '2024', '麦门冬', '养阴类'),
    ('天冬', '天冬', '2024', '天门冬', '养阴类'),
    ('化橘红', '化橘红', '2024', '', '化痰类、理气类'),
]

# 现有库用了别的叫法 → 映射到目录通用名
ALIAS_TO_CANON = {
    '薏米': '薏苡仁', '苡仁': '薏苡仁',
    '红枣': '枣', '大枣': '枣', '黑枣': '枣',
    '桂圆': '龙眼肉', '桂圆肉': '龙眼肉',
    '陈皮': '橘皮',
    '石斛': '铁皮石斛',
    '生姜': '姜', '干姜': '姜',
    '枸杞': '枸杞子',
    '双花': '金银花', '忍冬花': '金银花',
    '芝麻': '黑芝麻',
    '海带': '昆布',
}

PENDING = ['four_natures', 'five_flavors', 'meridian_tropism',
           'efficacy_chinese', 'dosage', 'contraindication']

CAT_SRC = '国家卫健委食药物质目录（2024 年第 4 号公告，累计 106 种）'


def canon(name):
    n = (name or '').strip()
    return ALIAS_TO_CANON.get(n, n)


def norm(s):
    return (s or '').strip()


def fullness(item):
    """字段非空数量，用于重复条目合并时挑保留哪个"""
    n = 0
    for k, v in item.items():
        if k in ('id', 'source', 'description'):
            continue
        if isinstance(v, list):
            n += len(v)
        elif v not in (None, '', []):
            n += 1
    return n


def merge_duplicates(ing):
    """把叫法不同但同一品种的条目合并（如 姜/生姜、枣/红枣、橘皮/陈皮）。
    保留字段更全的那个，被合并的名字写进 alias，并返回 旧名→保留名 的重命名表。"""
    groups = {}
    for item in ing:
        groups.setdefault(canon(item['name']), []).append(item)

    rename = {}
    kept = []
    for cn, items in groups.items():
        if len(items) == 1:
            kept.append(items[0])
            continue
        items.sort(key=fullness, reverse=True)
        main = items[0]
        for other in items[1:]:
            rename[norm(other['name'])] = norm(main['name'])
            old_alias = [x for x in (main.get('alias') or '').split('、') if x]
            if norm(other['name']) not in old_alias:
                old_alias.append(norm(other['name']))
            for a in [x for x in (other.get('alias') or '').split('、') if x]:
                if a not in old_alias:
                    old_alias.append(a)
            main['alias'] = '、'.join(old_alias)
            # 字段互补：保留条目空缺的，从被合并条目里补
            for k in ('four_natures', 'efficacy_chinese', 'nutrition_info',
                      'contraindication', 'dosage', 'source_lesson', 'source'):
                if not main.get(k) and other.get(k):
                    main[k] = other[k]
            for k in ('five_flavors', 'meridian_tropism', 'suitable_seasons',
                      'suitable_constitutions', 'cooking_methods',
                      'good_combinations', 'bad_combinations'):
                if not main.get(k) and other.get(k):
                    main[k] = other[k]
        kept.append(main)
    kept.sort(key=lambda x: x.get('id') or 0)
    return kept, rename


def apply_rename(rename):
    """食材改名后，菜谱里引用的名字要跟着改，否则匹配不上"""
    path = os.path.join(DATA, 'dishes.json')
    dishes = json.load(open(path, encoding='utf-8'))
    n = 0
    for d in dishes:
        for key in ('main_ingredients', 'auxiliary_ingredients', 'medicinal_ingredients'):
            for it in (d.get(key) or []):
                nm = norm(it.get('name'))
                if nm in rename:
                    it['name'] = rename[nm]
                    n += 1
    json.dump(dishes, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return len(dishes), n


def main():
    ing = json.load(open(os.path.join(DATA, 'ingredients.json'), encoding='utf-8'))

    ing, rename = merge_duplicates(ing)
    if rename:
        n_dish, n_ref = apply_rename(rename)
        print('合并重复条目    :', rename)
        print('菜谱引用改名    : %d 道菜 / %d 处' % (n_dish, n_ref))

    by_name = {norm(i['name']): i for i in ing}
    canon_index = {}
    for i in ing:
        canon_index.setdefault(canon(i['name']), []).append(i)

    catalog = {c[0]: c for c in CATALOG}
    assert len(CATALOG) == 106, '目录应为 106 种，实际 %d' % len(CATALOG)

    # ---- 1. 现有条目：校准归属 ----
    fixed, cleared = [], []
    for name, item in list(by_name.items()):
        cn = canon(name)
        if cn in catalog:
            c = catalog[cn]
            if item.get('in_catalog') != 1:
                fixed.append((name, cn))
            item['in_catalog'] = 1
            item['catalog_confirmed'] = 1
            item['catalog_batch'] = BATCH[c[2]]
            item['catalog_official'] = c[1]
            item['catalog_note'] = '在目录内'
            if not item.get('category'):
                item['category'] = c[4]
                item['category_source'] = '中药学常规分类（待课件核对）'
        else:
            # 不在 106 种目录内：普通食品/食材不适用该目录，法律属性应为 null
            if item.get('in_catalog') == 1:
                cleared.append(name)
            item['in_catalog'] = None
            item.pop('catalog_confirmed', None)
            item['catalog_batch'] = None
            item['catalog_official'] = None
            item['catalog_note'] = '普通食品/食材，不在食药物质目录内，不适用「药食同源」标注'

    # ---- 2. 新增缺失品种 ----
    added = []
    next_id = max((i.get('id') or 0) for i in ing) + 1
    for c in CATALOG:
        cname, official, batch, alias, cat = c
        if cname in canon_index:
            # 库里已有同一品种（可能叫法不同），补上官方名与别名即可，不重复建条目
            exist = canon_index[cname][0]
            if not exist.get('alias') and alias:
                exist['alias'] = alias
            continue
        item = {
            'id': next_id,
            'name': cname,
            'alias': alias,
            'category': cat,
            'category_source': '中药学常规分类（待课件核对）',
            'four_natures': None,
            'five_flavors': [],
            'meridian_tropism': [],
            'efficacy_chinese': None,
            'nutrition_info': None,
            'suitable_seasons': [],
            'suitable_constitutions': [],
            'contraindication': None,
            'dosage': None,
            'cooking_methods': [],
            'good_combinations': [],
            'bad_combinations': [],
            'in_catalog': 1,
            'catalog_confirmed': 1,
            'catalog_batch': BATCH[batch],
            'catalog_official': official,
            'catalog_note': '在目录内',
            'description': '%s。性味归经等待课件核对后补录。' % BATCH[batch],
            'is_medicinal': 1,
            'source_lesson': None,
            'source': CAT_SRC,
            'pending_fields': list(PENDING),
        }
        ing.append(item)
        by_name[cname] = item
        added.append(cname)
        next_id += 1

    # ---- 3. 用资料包第五部分回填性味（有依据才填） ----
    filled = []
    pack_nature = {p['name']: p for p in PACK['ingredients']}
    for name, item in by_name.items():
        p = pack_nature.get(name) or pack_nature.get(canon(name))
        if not p:
            continue
        nat = (p.get('nature') or '').split('/')
        if nat and nat[0] and not item.get('four_natures'):
            item['four_natures'] = nat[0]
        if len(nat) > 1 and nat[1] and not item.get('five_flavors'):
            item['five_flavors'] = [x for x in nat[1] if x]
        if p.get('nutrition') and not item.get('nutrition_info'):
            item['nutrition_info'] = p['nutrition']
        if p.get('cook') and not item.get('cooking_methods'):
            item['cooking_methods'] = [x for x in p['cook'].replace('、', ',').split(',') if x]
        if p.get('pair') and not item.get('good_combinations'):
            item['good_combinations'] = [x for x in p['pair'].replace('、', ',').split(',') if x]
        item['source'] = (item.get('source') or '') + '；性味与营养特点：资料包 V1.0 第五部分'
        if item.get('pending_fields'):
            item['pending_fields'] = [f for f in item['pending_fields']
                                      if not item.get(f)]
        filled.append(name)

    json.dump(ing, open(os.path.join(DATA, 'ingredients.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    n_cat = sum(1 for i in ing if i.get('in_catalog') == 1)
    print('食材总数        :', len(ing))
    print('目录内（106种） :', n_cat)
    print('本次改为目录内  :', len(fixed), fixed[:12])
    print('本次清出目录    :', len(cleared), cleared)
    print('新增品种        :', len(added))
    print('资料包回填性味  :', len(filled))
    print('待补字段品种数  :', sum(1 for i in ing if i.get('pending_fields')))


if __name__ == '__main__':
    main()
