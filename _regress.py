# -*- coding: utf-8 -*-
"""P2 全量回归：35 菜 × 8 人群 × 9 体质 = 2520 组合，比对基线防止退化"""
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from database import SessionLocal
from models import Dish, Ingredient, Constitution
from engine.matcher import Matcher
from engine.validator import SafetyValidator

BASELINE = {'block': 126, 'warn': 165}

db = SessionLocal()
matcher = Matcher(db)
validator = SafetyValidator()
ing_index = matcher.build_ingredient_index()

dishes = db.query(Dish).all()
constitutions = db.query(Constitution).all()
groups = list(validator.GROUP_NAME.keys())

cnt = Counter()
block_dishes = Counter()
combos = 0

for g in groups:
    for c in constitutions:
        for d in dishes:
            issues = validator.validate_dish(d, ing_index, g, c.name)
            combos += 1
            for i in issues:
                cnt[i['level']] += 1
                if i['level'] == 'block':
                    block_dishes[d.name] += 1

print('组合数:', combos)
print('分级命中:', dict(cnt))
print()
print('对照基线:', BASELINE)
for k, v in BASELINE.items():
    got = cnt.get(k, 0)
    flag = '✅ 无退化' if got == v else ('⚠️ 变化 %+d' % (got - v))
    print('  %-6s 基线 %4d → 现在 %4d  %s' % (k, v, got, flag))
print()
print('触发红线的菜（%d 道）：' % len(block_dishes))
for name, n in block_dishes.most_common():
    print('  %-16s %d 次' % (name, n))
db.close()
