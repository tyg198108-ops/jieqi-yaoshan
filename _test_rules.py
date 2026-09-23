# -*- coding: utf-8 -*-
"""规则引擎冒烟测试：用真实数据验证 rules v2.0 是否被正确消费"""
import sys, os, json
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from engine.validator import SafetyValidator

DATA = os.path.join(ROOT, 'backend', 'data')
dishes = json.load(open(os.path.join(DATA, 'dishes.json'), encoding='utf-8'))
ingredients = json.load(open(os.path.join(DATA, 'ingredients.json'), encoding='utf-8'))
idx = {x['name']: x for x in ingredients}

v = SafetyValidator()

CASES = [
    ('当归生姜羊肉汤', 'pregnant', '阳虚质'),
    ('当归生姜羊肉汤', 'none', '阳虚质'),
    ('荷叶山楂饮', 'pregnant', '痰湿质'),
    ('薏米相关', 'pregnant', None),
    ('黄芪汽锅鸡', 'elderly', '气虚质'),
    ('枸杞菊花茶', 'none', '阴虚质'),
    ('石斛老鸭汤', 'none', '阳虚质'),
]

for name, group, const in CASES:
    d = next((x for x in dishes if name in x['name']), None)
    if d is None:
        continue
    dish = SimpleNamespace(
        main_ingredients=d.get('main_ingredients'),
        medicinal_ingredients=d.get('medicinal_ingredients'),
        auxiliary_ingredients=d.get('auxiliary_ingredients'),
    )
    print('=' * 72)
    print(f'【{d["name"]}】人群={v.GROUP_NAME.get(group)}  体质={const}')
    issues = v.validate_dish(dish, idx, group, const)
    if not issues:
        print('  无提示')
    for it in issues:
        flag = {'block': '🚫', 'warn': '⚠️ ', 'tip': '💡'}.get(it['level'], '  ')
        conf = '' if it.get('confirmed', True) else ' [推断]'
        print(f'  {flag} [{it["level"]:5s}] {it["type"]}: {it["detail"]}{conf}')
        if it.get('source_lesson'):
            print(f'        出处: {it["source_lesson"]}')
    print(f'  >> 是否触发红线: {"是" if v.has_block(issues) else "否"}')

print('=' * 72)
print('合规检查示例：')
for t in ['本品可治疗高血压', '调理体质，养生保健', '不用吃药，吃了就好']:
    print(f'  "{t}" -> {v.check_compliance(t) or "合规 ✓"}')
