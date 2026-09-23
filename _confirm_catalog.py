# -*- coding: utf-8 -*-
"""
胡老师 2026-09-23 批量确认：食材库内全部药用食材（含此前待定的 27 味）
均按「药食同源」处理 -> in_catalog = 1, catalog_confirmed = 1
"""
import json, io, os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'data')
ing_path = os.path.join(DATA, 'ingredients.json')

with io.open(ing_path, encoding='utf-8') as f:
    ing = json.load(f)

NOTE = '胡老师核定：计入药食同源目录（2026-09-23 批量确认）'
changed = []
for x in ing:
    if x.get('is_medicinal') == 1 and not x.get('catalog_confirmed'):
        x['in_catalog'] = 1
        x['catalog_confirmed'] = 1
        x['catalog_note'] = NOTE
        changed.append(x['name'])

with io.open(ing_path, 'w', encoding='utf-8') as f:
    json.dump(ing, f, ensure_ascii=False, indent=2)

med = [x for x in ing if x.get('is_medicinal') == 1]
plain = [x for x in ing if x.get('is_medicinal') == 0]
pending = [x for x in med if not x.get('catalog_confirmed')]

print('本次确认 %d 味：' % len(changed))
print('  ' + '、'.join(changed))
print()
print('药用食材 %d 味 —— 目录已确认 %d 味，仍待定 %d 味' %
      (len(med), len(med) - len(pending), len(pending)))
print('普通食材 %d 味 —— in_catalog 均为 null（普通食品，不适用该目录）' % len(plain))
print('  校验 null 数量:', sum(1 for x in plain if x.get('in_catalog') is None))

# 规则库记录这次批量决策
rules_path = os.path.join(DATA, 'rules.json')
with io.open(rules_path, encoding='utf-8') as f:
    rules = json.load(f)
rules.setdefault('_meta', {}).setdefault('decisions', {})['Q1_catalog'] = (
    '全部药用食材（30 味）均计入药食同源目录：'
    '黄芪/当归/人参（2026-09-23 首批确认）+ 其余 27 味（同日批量确认）'
)
rules['_meta']['catalog_scope'] = {
    'confirmed_at': '2026-09-23',
    'confirmed_by': '胡老师',
    'note': '食材库 30 味药用食材全部按药食同源处理；53 味普通食材不适用该目录（in_catalog=null）',
    'pending': ['药食同源目录的官方版本号 / 批次仍未导入（台账 Q1 剩余部分）'],
}
with io.open(rules_path, 'w', encoding='utf-8') as f:
    json.dump(rules, f, ensure_ascii=False, indent=2)
print()
print('规则库 _meta.catalog_scope 已更新')
print('下一步：python _sync_frontend.py')
