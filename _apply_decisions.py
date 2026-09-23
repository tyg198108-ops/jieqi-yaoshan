# -*- coding: utf-8 -*-
"""
固化胡老师 2026-09-23 的四项决策：
  Q1  黄芪 / 当归 / 人参 计入药食同源目录   -> in_catalog = 1
  Q3  7 天为一疗程                          -> rules.treatment_course
  Q4  冲突裁决优先级确认                    -> rules.adjudication_priority（显式可配）
  Q18 课件为胡老师原创，可商用              -> _meta.copyright
另修正一处语义 BUG：普通食材的 in_catalog 由 0 改为 null（"不适用"），
                    避免将来误显示成"非药食同源 / 不能卖"。
"""
import json, io, os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'data')
CONFIRMED_AT = '2026-09-23'
CONFIRMED_BY = '胡老师核定'


def load(name):
    with io.open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def save(name, obj):
    with io.open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print('  已写入 %s' % name)


# ============ 1. 食材库：Q1 目录归属 ============
print('[1] 食材库 · Q1 药食同源目录归属')
ing = load('ingredients.json')

Q1_CONFIRMED = {
    '黄芪': '胡老师核定：计入药食同源目录（2026-09-23）',
    '当归': '胡老师核定：计入药食同源目录（2026-09-23）',
    '人参': '胡老师核定：计入药食同源目录（2026-09-23）。注意：人工种植人参另有试点管理与日用量限制，对外文案仍须标注用量',
}
changed = []
for x in ing:
    name = x['name']
    if name in Q1_CONFIRMED:
        old = x.get('in_catalog')
        x['in_catalog'] = 1
        x['catalog_note'] = Q1_CONFIRMED[name]
        x['catalog_confirmed'] = 1
        changed.append('%s(%s->1)' % (name, old))
    elif x.get('is_medicinal') == 1 and not x.get('catalog_confirmed'):
        # 其余药材：目录归属仍未核定，置空不再写 0，避免"假阴性"
        x['in_catalog'] = None
        x.setdefault('catalog_note', '药食同源目录归属待核定')
    elif x.get('is_medicinal') == 0:
        # 语义修正：普通食品不适用药食同源目录，不是"不在目录里"
        if x.get('in_catalog') == 0:
            x['in_catalog'] = None
        x.setdefault('catalog_note', '普通食品，不适用药食同源目录')
print('  已确认:', '、'.join(changed))
print('  普通食材 in_catalog 归位为 null 的共 %d 味' %
      sum(1 for x in ing if x.get('is_medicinal') == 0 and x.get('in_catalog') is None))
save('ingredients.json', ing)

# ============ 2. 规则库：Q3 疗程 + Q4 裁决优先级 + Q18 版权 ============
print()
print('[2] 规则库 · Q3 疗程 / Q4 裁决优先级 / Q18 版权')
rules = load('rules.json')

# Q3 疗程：只固化"7 天一疗程"，间隔天数课件未涉及 -> 明确留空不编
rules['treatment_course'] = {
    "_comment": "胡老师 2026-09-23 核定：7 天为一疗程。间隔天数、长期服用上限课件未涉及，一律留空，禁止臆造。",
    "default_days": 7,
    "confirmed": True,
    "confirmed_by": CONFIRMED_BY,
    "confirmed_at": CONFIRMED_AT,
    "items": [
        {
            "scope": "medicated",
            "scope_label": "药用膳方（含药材的汤/羹/茶/酒/膏）",
            "days": 7,
            "advice": "连续服用 7 天为一疗程；一疗程结束后观察身体反应再决定是否继续",
            "level": "tip",
            "source": CONFIRMED_BY + " " + CONFIRMED_AT
        },
        {
            "scope": "daily",
            "scope_label": "日常食养（不含药材的普通膳食）",
            "days": None,
            "advice": "可作日常饮食长期食用，不设疗程限制",
            "level": "tip",
            "source": "按 Q3 推论，待确认"
        }
    ],
    "pending": [
        "疗程间隔天数（吃满 7 天后停几天再进入下一疗程）—— 课件未涉及",
        "是否按体质 / 膳方类别差异化疗程 —— 课件未涉及",
        "长期连续服用的总时长上限 —— 课件未涉及"
    ]
}

# Q4 裁决优先级：原本硬编码在打分里，现提为可配置项
rules['adjudication_priority'] = {
    "_comment": "冲突裁决优先级（胡老师 2026-09-23 确认）。数字越小优先级越高，高优先级直接压过低优先级。",
    "confirmed": True,
    "confirmed_by": CONFIRMED_BY,
    "confirmed_at": CONFIRMED_AT,
    "order": [
        {"rank": 1, "key": "legal_catalog", "label": "法律目录红线", "action": "block", "desc": "非药食同源、禁用品种，一票否决"},
        {"rank": 2, "key": "group_taboo", "label": "人群禁忌", "action": "block", "desc": "孕妇/哺乳期/儿童/过敏/慢病/术前等禁用食材"},
        {"rank": 3, "key": "pair_conflict", "label": "配伍相反相恶", "action": "block/warn", "desc": "十八反十九畏、相恶相畏"},
        {"rank": 4, "key": "constitution_taboo", "label": "体质宜忌", "action": "warn", "desc": "体质少吃 / 通类伤正"},
        {"rank": 5, "key": "term_fit", "label": "节气适配", "action": "score", "desc": "当季当地当体质"},
        {"rank": 6, "key": "taste_cost", "label": "口味与成本", "action": "score", "desc": "同分时的兜底排序"}
    ],
    "score_delta": {
        "_comment": "与前端 scoreDish / 后端 matcher 保持一致，改这里需同步改代码",
        "block": -300, "warn": -80, "tip": -5, "synergy": 15
    }
}

# 剂量表注释：Q3 已确认，去掉"疗程待确认"字样
rules['dosage_limits']['_comment'] = '单次参考量（课件原文）。疗程标准见 treatment_course：7 天为一疗程（胡老师 2026-09-23 核定）'

# Q18 版权
rules.setdefault('_meta', {})
rules['_meta'].update({
    "copyright": "课件内容为胡老师原创，授权本产品商用（2026-09-23 确认）",
    "copyright_confirmed": True,
    "decisions": {
        "Q1_catalog": "黄芪/当归/人参计入药食同源目录（2026-09-23 胡老师核定）",
        "Q3_course": "7 天为一疗程（2026-09-23 胡老师核定）",
        "Q4_priority": "裁决优先级确认（2026-09-23 胡老师核定）",
        "Q18_copyright": "课件原创，可商用（2026-09-23 胡老师确认）"
    }
})
save('rules.json', rules)

print()
print('[3] 校验')
r = load('rules.json')
print('  treatment_course.default_days =', r['treatment_course']['default_days'])
print('  裁决优先级 %d 级，分值 %s' % (len(r['adjudication_priority']['order']),
                                      r['adjudication_priority']['score_delta']))
print('  版权:', r['_meta']['copyright'][:40] + '...')
i2 = load('ingredients.json')
for n in ['黄芪', '当归', '人参']:
    x = next(a for a in i2 if a['name'] == n)
    print('  %s: in_catalog=%s confirmed=%s' % (n, x['in_catalog'], x.get('catalog_confirmed')))
print('  仍待核定的药材:', [x['name'] for x in i2
                            if x.get('is_medicinal') == 1 and not x.get('catalog_confirmed')] or '无')
print()
print('完成。下一步：python _sync_frontend.py')
