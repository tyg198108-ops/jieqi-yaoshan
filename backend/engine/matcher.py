from typing import List, Dict, Tuple, Any
from sqlalchemy.orm import Session
from models import Dish, Ingredient, SolarTerm, Constitution

class Matcher:
    def __init__(self, db: Session):
        self.db = db

    def build_ingredient_index(self) -> Dict[str, Any]:
        """构建 食材名/别名 -> Ingredient 的索引，供通类伤正规则判断功效分类"""
        idx = {}
        for ing in self.db.query(Ingredient).all():
            idx[ing.name] = ing
            for a in (ing.alias or '').replace('，', '、').split('、'):
                a = a.strip()
                if a:
                    idx[a] = ing
        return idx

    @staticmethod
    def _level_penalty(level: str) -> int:
        """分级扣分：block 直接否决，warn 明显降权，tip 轻微"""
        return {'block': -300, 'warn': -80, 'tip': -5, 'good': 15}.get(level, 0)

    def score_dish_for_solar_term(self, dish: Dish, solar_term: SolarTerm) -> int:
        """给菜品对节气的匹配度打分"""
        score = 0
        if not dish.suitable_seasons:
            return 0
        
        # 精确匹配节气名称
        if solar_term.name in dish.suitable_seasons:
            score += 100
        
        # 匹配季节
        if solar_term.season in dish.suitable_seasons:
            score += 50
        
        # 匹配相邻节气（同季节）
        for term_name in dish.suitable_seasons:
            if term_name in solar_term.recommended_ingredients:
                score += 10
        
        return score
    
    def score_dish_for_constitution(self, dish: Dish, constitution: Constitution) -> int:
        """给菜品对体质的匹配度打分"""
        score = 0
        if not dish.suitable_constitutions:
            return 30  # 平性菜品基础分
        
        if constitution.name in dish.suitable_constitutions:
            score += 100
        
        if '平和质' in dish.suitable_constitutions:
            score += 20
        
        # 排除禁忌体质：检查是否在禁忌食材中，这里简化处理
        return score
    
    def get_seasonal_dishes(self, solar_term: SolarTerm, dish_type: str,
                          main_constitution: Constitution,
                          secondary_constitution: Constitution = None,
                          special_group: str = None,
                          limit: int = 10,
                          allow_low: bool = True,
                          dish_types: List[str] = None) -> List[Tuple[Dish, int, List[Dict[str, Any]]]]:
        """获取符合节气和体质的推荐菜品，按评分排序。
        第三项为**结构化分级问题列表**（含 level/type/detail/source_lesson），
        不是字符串——上层用 SafetyValidator.to_alerts() 转前端渲染结构。

        dish_types：可传类型列表（席单按「席位」取菜时一个席位可能有多种备选类型）。
        allow_low：池子里没有正分菜时，是否退回最高分（哪怕 <=0）。
        以前一律返回空，上层只能随便抓一道菜顶位置，出品会离谱；现在宁可低分同源类型。
        """
        from engine.validator import SafetyValidator
        validator = SafetyValidator()
        ing_index = self.build_ingredient_index()

        if dish_types:
            types = list(dish_types)
        elif isinstance(dish_type, (list, tuple)):
            types = list(dish_type)
        else:
            types = [dish_type]

        query = self.db.query(Dish).filter(Dish.dish_type.in_(types))
        all_dishes = query.all()

        scored_dishes = []
        for dish in all_dishes:
            score = 0
            issues_acc: List[Dict[str, Any]] = []

            # 节气匹配
            score += self.score_dish_for_solar_term(dish, solar_term)

            # 主体质匹配
            score += self.score_dish_for_constitution(dish, main_constitution)

            # 兼夹体质调整
            if secondary_constitution:
                sub_score = self.score_dish_for_constitution(dish, secondary_constitution)
                if sub_score > 0:
                    score += sub_score * 0.5
                else:
                    score -= 30  # 不适合兼夹体质扣分

            # 分级安全校验：人群禁忌 + 配伍七情 + 通类伤正 + 单味禁忌 + 用量 + 协同
            issues = validator.validate_dish(
                dish, ing_index,
                special_group or 'none',
                main_constitution.name if main_constitution else None,
            )
            for it in issues:
                score += self._level_penalty(it['level'])
            issues_acc = issues

            # 四气平衡（简化处理：根据体质寒热调整）
            if main_constitution.code in ['yangxu', 'qixu']:
                # 阳虚气虚偏寒，适合温性菜
                if dish.flavor in ['浓郁', '咸鲜', '香辣']:
                    score += 20
            if main_constitution.code in ['yinxu', 'shire']:
                # 阴虚湿热偏热，适合清淡凉性菜
                if dish.flavor in ['清淡', '鲜甜', '清爽']:
                    score += 20

            # 菜单菜（金陵老味道等）没有功效/性味记载，评分为 0 也要入池：
            # 否则新补的菜永远选不上，席位只能反复出老几样。
            # 红线菜分数被扣成大负数，自然沉底，上层还有 has_block 过滤。
            scored_dishes.append((dish, score, issues_acc))

        # 按分数排序
        scored_dishes.sort(key=lambda x: x[1], reverse=True)
        if len(scored_dishes) >= limit or not allow_low:
            return scored_dishes[:limit]

        # 正分池不够坐满席位：用同类型里剩下的菜补足（分数可能 <=0）。
        # 不补的话，席单后段会被迫跨类型抓菜——素菜位上端鱼、凉菜位上端粥。
        # 补足项仍按分数排在后面，正分的永远优先；红线由上层 has_block 再挡一道。
        picked_ids = {d.id for d, _, _ in scored_dishes}
        low = []
        for dish in all_dishes:
            if dish.id in picked_ids:
                continue
            score = self.score_dish_for_solar_term(dish, solar_term) + \
                    self.score_dish_for_constitution(dish, main_constitution)
            issues = validator.validate_dish(
                dish, ing_index,
                special_group or 'none',
                main_constitution.name if main_constitution else None,
            )
            for it in issues:
                score += self._level_penalty(it['level'])
            low.append((dish, score, issues))
        low.sort(key=lambda x: x[1], reverse=True)
        return (scored_dishes + low)[:limit]
    
    def get_match_reason(self, dish: Dish, solar_term: SolarTerm, constitution: Constitution) -> str:
        """生成菜品匹配理由"""
        reasons = []
        if solar_term.name in (dish.suitable_seasons or []):
            reasons.append(f'{solar_term.name}时令菜品')
        elif solar_term.season in (dish.suitable_seasons or []):
            reasons.append(f'{solar_term.season}季{solar_term.name}适宜')
        
        if constitution.name in (dish.suitable_constitutions or []):
            reasons.append(f'适合{constitution.name}体质')
        
        # 资料包菜谱没有中医功效字段（资料没给，不臆造），退回膳食搭配定位；
        # 两者都没有就只保留时令/体质理由，不再硬切片（曾因 None 直接 500）
        summary = dish.efficacy_chinese or dish.nutrition_info
        if summary:
            reasons.append(summary[:30] + ('...' if len(summary) > 30 else ''))
        return '；'.join(reasons) or '按节气与体质匹配'
