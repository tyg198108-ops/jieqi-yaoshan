import json
import os
from typing import List, Dict, Any

class SafetyValidator:
    def __init__(self):
        rules_path = os.path.join(os.path.dirname(__file__), '../data/rules.json')
        with open(rules_path, 'r', encoding='utf-8') as f:
            self.rules = json.load(f)
    
    def get_special_group_forbidden(self, special_group: str) -> List[str]:
        """获取特殊人群禁忌食材列表"""
        if special_group in self.rules['special_group_contraindications']:
            return self.rules['special_group_contraindications'][special_group]['forbidden_ingredients']
        return []
    
    def get_special_group_warning(self, special_group: str) -> str:
        if special_group in self.rules['special_group_contraindications']:
            return self.rules['special_group_contraindications'][special_group]['warning']
        return ''
    
    def check_ingredient_conflict(self, ingredient1: str, ingredient2: str) -> bool:
        """检查两种食材是否有配伍禁忌"""
        if ingredient1 in self.rules['ingredient_contraindications']:
            if ingredient2 in self.rules['ingredient_contraindications'][ingredient1]:
                return True
        if ingredient2 in self.rules['ingredient_contraindications']:
            if ingredient1 in self.rules['ingredient_contraindications'][ingredient2]:
                return True
        return False
    
    def validate_dish_for_special_group(self, dish, special_group: str) -> List[str]:
        """校验菜品是否适合特殊人群，返回警告列表"""
        warnings = []
        forbidden = self.get_special_group_forbidden(special_group)
        
        # 检查主料
        all_ingredients = []
        if dish.main_ingredients:
            all_ingredients.extend([ing['name'] for ing in dish.main_ingredients])
        if dish.medicinal_ingredients:
            all_ingredients.extend([ing['name'] for ing in dish.medicinal_ingredients])
        if dish.auxiliary_ingredients:
            all_ingredients.extend([ing['name'] for ing in dish.auxiliary_ingredients])
        
        for ing in all_ingredients:
            for forbid in forbidden:
                if forbid in ing:
                    warnings.append(f'本品含{forbid}，{self.rules["special_group_contraindications"][special_group]["name"]}慎用')
        
        return warnings
    
    def check_compliance(self, text: str) -> List[str]:
        """检查文案合规性，返回违规词汇列表"""
        issues = []
        banned = self.rules['compliance_phrases']['banned_words']
        for word in banned:
            if word in text:
                issues.append(f'使用了违规宣传词汇：{word}')
        return issues

    def get_disclaimer(self) -> str:
        return self.rules['compliance_phrases']['disclaimer']

    # ==================== 以下为 rules v2.0 新增能力 ====================

    # 特殊人群 key -> 人群描述关键词（用于匹配 ingredient_cautions / category_cautions 的中文人群表述）
    GROUP_KEYWORDS = {
        'pregnant': ['孕', '胎'],
        'lactating': ['哺乳', '乳汁', '婴儿'],
        'children': ['儿童', '小儿', '婴幼儿'],
        'elderly': ['老年', '老人'],
        'allergy': ['过敏'],
        'chronic': ['慢病', '高血压', '糖尿病', '慢性病'],
        'surgery': ['手术'],
    }

    def _group_match(self, caution_groups: List[str], special_group: str) -> bool:
        """判断某条规则的慎用人群是否命中当前特殊人群"""
        if not special_group or special_group == 'none':
            return False
        kws = self.GROUP_KEYWORDS.get(special_group, [])
        return any(any(k in g for k in kws) for g in (caution_groups or []))

    def _constitution_match(self, caution_groups: List[str], constitution_name: str) -> bool:
        """判断某条规则的慎用人群是否命中当前体质（如『阴虚质』匹配『阴虚明显者』）"""
        if not constitution_name:
            return False
        key = constitution_name.replace('质', '')
        if not key:
            return False
        return any(key in g for g in (caution_groups or []))

    def find_pair_rule(self, a: str, b: str):
        """查两味食材间的配伍规则，命中返回规则 dict，否则 None"""
        for r in self.rules.get('pair_rules', []):
            if (r['a'] in a or a in r['a']) and (r['b'] in b or b in r['b']):
                return r
            if (r['a'] in b or b in r['a']) and (r['b'] in a or a in r['b']):
                return r
        return None

    def find_synergy(self, a: str, b: str):
        """查两味食材间的正向协同（相须/相使）"""
        for r in self.rules.get('synergy_pairs', []):
            if (r['a'] in a or a in r['a']) and (r['b'] in b or b in r['b']):
                return r
            if (r['a'] in b or b in r['a']) and (r['b'] in a or a in r['b']):
                return r
        return None

    def check_dosage(self, ingredient_name: str) -> Dict[str, Any]:
        """返回该药材的剂量参考；课件未给出的返回 None"""
        limits = self.rules.get('dosage_limits', {})
        for k, v in limits.items():
            if k.startswith('_'):
                continue
            if k in ingredient_name or ingredient_name in k:
                return {'ingredient': k, **v}
        return None

    def validate_dish(
        self,
        dish,
        ingredient_index: Dict[str, Any] = None,
        special_group: str = 'none',
        constitution_name: str = None,
    ) -> List[Dict[str, Any]]:
        """
        对单道菜做分级安全校验，返回问题列表：
        [{'level': 'block'|'warn'|'tip', 'type': 规则类型, 'detail': 说明, 'source_lesson': 出处}]
        裁决优先级：法律目录红线 > 人群禁忌 > 相反/相恶 > 体质宜忌 > 节气适配
        """
        issues = []
        ingredient_index = ingredient_index or {}

        names = []
        for field in ('main_ingredients', 'medicinal_ingredients', 'auxiliary_ingredients'):
            for ing in (getattr(dish, field, None) or []):
                if isinstance(ing, dict):
                    names.append(ing.get('name'))
        names = [n for n in names if n]

        # 1) 特殊人群禁用食材
        for forbid in self.get_special_group_forbidden(special_group):
            for n in names:
                if n and forbid in n:
                    issues.append({
                        'level': 'block', 'type': '人群禁用',
                        'detail': f'含{forbid}，{self.GROUP_NAME.get(special_group, "该人群")}禁用',
                        'source_lesson': self.rules['special_group_contraindications'].get(special_group, {}).get('source_lesson', ''),
                    })

        # 2) 单味药材的人群/证候禁忌（第15课 P7 八味）
        for rule in self.rules.get('ingredient_cautions', []):
            ing_name = rule['ingredient']
            hit = [n for n in names if n and (ing_name in n or n in ing_name)]
            if not hit:
                continue
            if self._group_match(rule['caution_groups'], special_group) or \
               self._constitution_match(rule['caution_groups'], constitution_name):
                issues.append({
                    'level': rule['level'], 'type': '单味禁忌',
                    'detail': f"{ing_name}：{'、'.join(rule['caution_groups'])}慎用（{rule['reason']}）",
                    'source_lesson': rule.get('source_lesson', ''),
                })

        # 3) 通类伤正（第06课 P15）：活血/清热/祛湿/理气
        for rule in self.rules.get('category_cautions', []):
            key = rule['category_key']
            hit = []
            for n in names:
                obj = ingredient_index.get(n)
                # 索引值可能是 dict（离线测试）也可能是 ORM 对象（线上调用），两种都要兼容
                if isinstance(obj, dict):
                    cat = obj.get('category') or ''
                else:
                    cat = getattr(obj, 'category', '') or ''
                if key in cat:
                    hit.append(n)
            if not hit:
                continue
            if self._group_match(rule['caution_groups'], special_group) or \
               self._constitution_match(rule['caution_groups'], constitution_name):
                issues.append({
                    'level': rule['level'], 'type': '通类伤正',
                    'detail': f"{'、'.join(hit)}属{key}类，{'、'.join(rule['caution_groups'])}慎用（{rule['reason']}）",
                    'source_lesson': rule.get('source_lesson', ''),
                })

        # 4) 配伍禁忌（同一道菜内两两组合）
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                r = self.find_pair_rule(names[i], names[j])
                if r:
                    issues.append({
                        'level': r['level'], 'type': f"配伍-{r['type']}",
                        'detail': f"{names[i]} 与 {names[j]}：{r['reason']}",
                        'source_lesson': r.get('source_lesson', ''),
                        'confirmed': r.get('confirmed', True),
                    })

        # 5) 协同增效（相须/相使/相畏相杀，正向提示，来源第07课七情合和）
        syn_hits = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                r = self.find_synergy(names[i], names[j])
                if r:
                    syn_hits.append(f"{r['a']}+{r['b']}（{r['type']}·{r['effect']}）")
        if syn_hits:
            issues.append({
                'level': 'good', 'type': '协同增效',
                'detail': '、'.join(dict.fromkeys(syn_hits)),
                'source_lesson': '第07课 P7–P9 七情合和',
            })

        # 6) 剂量提示
        for n in names:
            d = self.check_dosage(n)
            if d:
                issues.append({
                    'level': 'tip', 'type': '剂量参考',
                    'detail': f"{d['ingredient']} 建议 {d['amount']}",
                    'source_lesson': d.get('source_lesson', ''),
                })

        # ---- 疗程提示（Q3：胡老师 2026-09-23 核定 7 天为一疗程）----
        tc = self.rules.get('treatment_course') or {}
        items = tc.get('items') or []
        if items:
            is_medicated = False
            for n in names:
                obj = ingredient_index.get(n)
                if obj is None:
                    continue
                val = obj.get('is_medicinal') if isinstance(obj, dict) else getattr(obj, 'is_medicinal', None)
                if val == 1 or val is True:
                    is_medicated = True
                    break
            scope = 'medicated' if is_medicated else 'daily'
            item = next((x for x in items if x.get('scope') == scope), items[0])
            if item and item.get('advice'):
                issues.append({
                    'level': 'tip', 'type': '疗程',
                    'detail': item['advice'],
                    'source_lesson': item.get('source', ''),
                })

        # 去重（同 detail 只保留一条）
        seen, uniq = set(), []
        for it in issues:
            k = (it['level'], it['detail'])
            if k not in seen:
                seen.add(k)
                uniq.append(it)
        return uniq

    GROUP_NAME = {
        'pregnant': '孕妇', 'lactating': '哺乳期女性', 'children': '儿童',
        'elderly': '老年人', 'allergy': '过敏体质', 'chronic': '慢性病患者',
        'surgery': '手术前后', 'none': '普通人群',
    }

    def has_block(self, issues: List[Dict[str, Any]]) -> bool:
        """是否存在红线级问题（用于上层决定是否剔除该菜）"""
        return any(i['level'] == 'block' for i in issues)

    # ==================== 前端渲染用的结构化告警 ====================

    LEVEL_ICON = {'block': '🚫', 'warn': '⚠️', 'tip': '💡', 'good': '✨'}

    def to_alerts(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """把分级问题列表转成前端可直接渲染的 alerts（带图标、出处、推断标记）"""
        out = []
        for i in issues:
            level = i.get('level', 'tip')
            out.append({
                'level': level,
                'icon': self.LEVEL_ICON.get(level, '💡'),
                'type': i.get('type', ''),
                'msg': i.get('detail', ''),
                'src': i.get('source_lesson', ''),
                'flag': '' if i.get('confirmed', True) else '推断',
            })
        return out

    @staticmethod
    def stat_of(issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计 block / warn / tip 数量（good 不计入风险统计）"""
        return {
            'block': sum(1 for i in issues if i.get('level') == 'block'),
            'warn': sum(1 for i in issues if i.get('level') == 'warn'),
            'tip': sum(1 for i in issues if i.get('level') == 'tip'),
            'good': sum(1 for i in issues if i.get('level') == 'good'),
        }
