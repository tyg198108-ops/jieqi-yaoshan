# -*- coding: utf-8 -*-
"""食材品类与荤素判定：宴席硬结构（3荤3素冷菜、热菜覆盖五类）靠它做筛选。

判定口径全部来自「菜名 + 主料」的字面匹配，不反向编造数据：
库里没有虾就是没有虾，判不出来就如实报告缺位。
"""
import re

# 五类必覆 + 常见蛋豆，供席位 require 使用
SHRIMP = ('虾仁', '基围虾', '河虾', '青虾', '明虾', '大虾', '虾米', '海米', '龙虾', '虾')
FISH = ('鲈鱼', '鲫鱼', '鳜鱼', '草鱼', '带鱼', '黄花鱼', '鳕鱼', '三文鱼', '鱼片', '鱼块', '鱼')
LIVESTOCK = ('牛腩', '牛肉', '牛排', '牛腱', '羊排', '羊肉', '排骨', '五花肉', '里脊',
             '瘦肉', '猪蹄', '蹄筋', '火腿', '培根', '腊肉', '猪肉',
             # 金陵冷碟荤菜：菜名字面不含「猪肉」（猪头肉/口条/肉皮），需单列
             '猪头肉', '口条', '肉皮', '肴肉')
POULTRY = ('鸡胸肉', '鸡腿', '鸡翅', '土鸡', '乌鸡', '童子鸡', '鸡丁', '鸡肉', '鸭肉', '鸭', '鹅', '鸡')
# 蛋品、豆制品、根菜类归素（宴席口径里算素菜）
VEG_EXTRA = ('鸡蛋', '蛋液', '豆腐', '豆干', '香干', '腐竹', '豆浆', '皮蛋', '松花蛋')

# 海鲜里的贝类也算荤，但不属于五类必覆
OTHER_SEAFOOD = ('海蜇', '蜇头', '蛤', '贝', '蟹', '海参', '鲍鱼', '墨鱼', '鱿鱼')

TAG_LABEL = {
    'shrimp': '虾类', 'fish': '鱼类', 'livestock': '牛羊猪',
    'poultry': '鸡鸭禽', 'veg': '蔬菜', 'other': '其他',
}

_METHODS = ('蒸', '炖', '炒', '焖', '煮', '卤', '拌', '煲', '烩', '煎', '烤', '炸', '煨')


def _names(dish):
    """把菜的主辅料名与菜名拼成一个串，供关键词匹配"""
    parts = [dish.name or '']
    for field in ('main_ingredients', 'auxiliary_ingredients', 'medicinal_ingredients'):
        for ing in (getattr(dish, field, None) or []):
            if isinstance(ing, dict):
                nm = ing.get('name')
            else:
                nm = ing
            if nm:
                parts.append(nm)
    return ' '.join(parts)


def protein_tags(dish) -> set:
    """返回该菜属于哪几类：shrimp / fish / livestock / poultry / veg"""
    s = _names(dish)
    tags = set()
    if any(k in s for k in SHRIMP):
        tags.add('shrimp')
    if any(k in s for k in FISH):
        tags.add('fish')
    if any(k in s for k in LIVESTOCK):
        tags.add('livestock')
    if any(k in s for k in POULTRY):
        tags.add('poultry')
    if not tags:
        tags.add('veg')
    return tags


def is_meat(dish) -> bool:
    """荤：鱼虾禽畜贝蟹都算；只有纯素才 False"""
    return bool(protein_tags(dish) - {'veg'}) or any(k in _names(dish) for k in OTHER_SEAFOOD)


def method_of(dish) -> str:
    """出品技法：先看 cooking_method，再看菜名能不能推出一道主技法"""
    m = (getattr(dish, 'cooking_method', None) or '').strip()
    if m:
        return m
    for word in _METHODS:
        if word in (dish.name or ''):
            return word
    return ''


def has_herb(dish) -> bool:
    return bool(getattr(dish, 'medicinal_ingredients', None))


def herb_pairing(dish) -> str:
    """药膳配伍：把药材与主料串成一句可读的配伍说明"""
    items = []
    for ing in (getattr(dish, 'medicinal_ingredients', None) or []):
        nm = ing.get('name') if isinstance(ing, dict) else ing
        amt = (ing.get('amount') if isinstance(ing, dict) else None) or ''
        items.append(nm + ((' ' + amt) if amt else ''))
    return '、'.join(items)


def match_req(dish, req: str) -> bool:
    """席位要求是否满足：cold_meat/cold_veg/shrimp/fish/livestock/poultry/veg/herb"""
    if req == 'cold_meat':
        return is_meat(dish)
    if req == 'cold_veg':
        return not is_meat(dish)
    if req == 'herb':
        return has_herb(dish)
    if req == 'veg':
        return 'veg' in protein_tags(dish)
    return req in protein_tags(dish)


def tag_label(dish) -> str:
    """给菜品一句食材类别标注：虾类 / 鱼类 / 牛羊猪 / 鸡鸭禽 / 水产 / 时蔬"""
    tags = protein_tags(dish)
    if tags == {'veg'} and any(k in _names(dish) for k in OTHER_SEAFOOD):
        # 海蜇、蟹、贝这些既不在五类里、又不是素的，
        # 不特殊处理的话「老醋蜇头」会被标成「蔬菜」端上荤盘冷碟位。
        return '水产'
    if len(tags) > 1:
        return ' + '.join(TAG_LABEL.get(t, t) for t in sorted(tags))
    return TAG_LABEL.get(next(iter(tags)), '时蔬')


COLD_HINT = re.compile(r'凉拌|拌菜|沙拉|卤|腌|白斩|冻')


def is_cold_dish(dish) -> bool:
    """是否为凉菜：冷碟类型，或菜名自带凉/卤/腌字样"""
    return getattr(dish, 'dish_type', '') == '冷碟' or bool(COLD_HINT.search(dish.name or ''))
