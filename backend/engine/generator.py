from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import SolarTerm, Constitution, Dish
from engine.matcher import Matcher
from engine.validator import SafetyValidator
from engine import taxonomy as tax
from schemas import BanquetResponse, BanquetDishItem, SolarTermDetail, ConstitutionDetail

class BanquetGenerator:
    # 席单结构：场景(banquet_type) + 规格(scale) -> 席位清单。
    # 一条席位 = {name 席位名, course 上菜分组, types 可选菜品类型（按顺序降级）}
    SCENE_STRUCTURE = {
        # 养生宴：胡老师 2026-09-23 定的硬结构
        # 6 冷菜（3 荤 3 素）+ 8 热菜（必覆虾/鱼/牛羊猪/鸡/蔬菜五类）+ 药膳汤 1
        # + 点心或主食 1（二选一）+ 茶饮 1 = 17 道（按 10 人席）
        'health': {
            'banquet': {
                'label': '节气养生宴',
                'seats': [
                    {'name': '迎宾冷碟（一）', 'course': 'cold', 'types': ['冷碟'], 'require': 'cold_meat', 'require_label': '荤'},
                    {'name': '迎宾冷碟（二）', 'course': 'cold', 'types': ['冷碟'], 'require': 'cold_meat', 'require_label': '荤'},
                    {'name': '迎宾冷碟（三）', 'course': 'cold', 'types': ['冷碟'], 'require': 'cold_meat', 'require_label': '荤'},
                    {'name': '爽口素碟（一）', 'course': 'cold', 'types': ['冷碟'], 'require': 'cold_veg', 'require_label': '素'},
                    {'name': '爽口素碟（二）', 'course': 'cold', 'types': ['冷碟'], 'require': 'cold_veg', 'require_label': '素'},
                    {'name': '爽口素碟（三）', 'course': 'cold', 'types': ['冷碟'], 'require': 'cold_veg', 'require_label': '素'},
                    {'name': '河鲜虾馔', 'course': 'hot', 'types': ['热菜', '素菜', '主菜'], 'require': 'shrimp', 'require_label': '虾类'},
                    {'name': '江河鱼馔', 'course': 'hot', 'types': ['热菜', '主菜', '素菜'], 'require': 'fish', 'require_label': '鱼类'},
                    {'name': '畜肉大菜', 'course': 'hot', 'types': ['热菜', '主菜'], 'require': 'livestock', 'require_label': '牛羊猪'},
                    {'name': '禽馔一味', 'course': 'hot', 'types': ['热菜', '主菜'], 'require': 'poultry', 'require_label': '鸡鸭禽'},
                    {'name': '时令蔬菜', 'course': 'hot', 'types': ['素菜', '热菜'], 'require': 'veg', 'require_label': '蔬菜'},
                    {'name': '时令热菜（六）', 'course': 'hot', 'types': ['热菜', '主菜']},
                    {'name': '时令热菜（七）', 'course': 'hot', 'types': ['热菜', '主菜', '素菜']},
                    {'name': '时令热菜（八）', 'course': 'hot', 'types': ['热菜', '主菜', '素菜']},
                    {'name': '节气药膳汤', 'course': 'soup', 'types': ['汤品'], 'require': 'herb', 'require_label': '含药材配伍'},
                    {'name': '药膳点心', 'course': 'dessert', 'types': ['甜品']},
                    {'name': '季节养生茶饮', 'course': 'drink', 'types': ['茶饮', '甜品', '汤品']},
                ],
            },
        },
        # 家庭餐：四菜一汤一饮（两荤两素 + 例汤 + 饮品），共 6 道
        'family': {
            'standard': {
                'label': '四菜一汤一饮',
                'seats': [
                    {'name': '家常菜（一）', 'course': 'hot', 'types': ['热菜', '主菜']},
                    {'name': '家常菜（二）', 'course': 'hot', 'types': ['热菜', '主菜']},
                    {'name': '时令素菜（一）', 'course': 'veg', 'types': ['素菜', '热菜']},
                    {'name': '时令素菜（二）', 'course': 'veg', 'types': ['素菜', '热菜']},
                    {'name': '家常例汤', 'course': 'soup', 'types': ['汤品']},
                    {'name': '养生饮品', 'course': 'drink', 'types': ['茶饮', '甜品', '汤品']},
                ],
            },
        },
        # 商务餐：2 道冷菜 + 4 道热菜 + 1 道汤 + 1 道饮品，共 8 道
        'business': {
            'standard': {
                'label': '两冷四热一汤一饮',
                'seats': [
                    {'name': '迎宾冷菜（一）', 'course': 'cold', 'types': ['冷碟']},
                    {'name': '迎宾冷菜（二）', 'course': 'cold', 'types': ['冷碟', '素菜']},
                    {'name': '商务热菜（一）', 'course': 'hot', 'types': ['热菜', '主菜']},
                    {'name': '商务热菜（二）', 'course': 'hot', 'types': ['热菜', '主菜']},
                    {'name': '商务热菜（三）', 'course': 'hot', 'types': ['主菜', '热菜']},
                    {'name': '商务热菜（四）', 'course': 'hot', 'types': ['热菜', '主菜']},
                    {'name': '席上例汤', 'course': 'soup', 'types': ['汤品']},
                    {'name': '佐餐饮品', 'course': 'drink', 'types': ['茶饮', '甜品', '汤品']},
                ],
            },
        },
    }

    COURSE_NAME = {
        'cold': '迎宾冷菜', 'hot': '热菜', 'veg': '时令素菜',
        'soup': '汤品', 'staple': '主食', 'dessert': '羹品甜品', 'drink': '饮品',
    }

    SCENE_NAME = {'health': '养生宴', 'family': '家庭餐', 'business': '商务餐'}

    def __init__(self, db: Session):
        self.db = db
        self.matcher = Matcher(db)
        self.validator = SafetyValidator()

    def structure_of(self, banquet_type: str, scale: str = None):
        """取席单结构：场景 + 规格。传错场景或规格时退回养生正席，不抛错。"""
        scene = self.SCENE_STRUCTURE.get(banquet_type) or self.SCENE_STRUCTURE['health']
        if scale and scale in scene:
            return scene[scale]
        return scene.get('standard') or list(scene.values())[0]

    @staticmethod
    def _main_keys(dish) -> set:
        keys = set()
        for field in ('main_ingredients', 'medicinal_ingredients'):
            for ing in (getattr(dish, field, None) or []):
                name = (ing or {}).get('name') if isinstance(ing, dict) else None
                if name:
                    keys.add(name)
        return keys

    def generate(self, solar_term_id: int, main_constitution_id: int,
                secondary_constitution_id: int = None,
                special_group: str = None,
                banquet_type: str = 'health',
                flavor_preference: str = None,
                banquet_scale: str = None,
                headcount: int = 10,
                finale: str = 'dessert') -> BanquetResponse:

        # 获取节气和体质
        solar_term = self.db.query(SolarTerm).filter(SolarTerm.id == solar_term_id).first()
        main_constitution = self.db.query(Constitution).filter(Constitution.id == main_constitution_id).first()
        secondary_constitution = None
        if secondary_constitution_id:
            secondary_constitution = self.db.query(Constitution).filter(Constitution.id == secondary_constitution_id).first()

        if not solar_term or not main_constitution:
            raise ValueError('节气或体质不存在')

        # 席单结构：场景决定道数与席位。养生宴只有一种硬结构（17 道）
        struct = self.structure_of(banquet_type, banquet_scale)
        seats = struct['seats']
        if banquet_type == 'health':
            # 收尾一道：药膳点心 或 养生主食，二选一
            seats = [dict(s) for s in seats]
            for s in seats:
                if s['course'] == 'dessert':
                    if finale == 'staple':
                        s.update(name='养生主食', course='staple', types=['主食'])
                    break
        try:
            headcount = max(1, min(30, int(headcount or 10)))
        except (TypeError, ValueError):
            headcount = 10

        # 生成各道菜品
        dishes = []
        all_shopping_list = set()
        safety_warnings = []

        # 特殊人群警告
        if special_group and special_group != 'none':
            warn = self.validator.get_special_group_warning(special_group)
            if warn:
                safety_warnings.append(warn)

        used_dish_ids = set()
        used_main_keys = set()
        used_methods = set()
        tag_used: Dict[str, int] = {}
        # 没滿足的席位要求：如实上报，不拿不相干的菜硬凑
        unmet: List[Dict[str, str]] = []
        # 食材索引只构建一次（每道菜都查一次库会拖慢生成）
        ing_index_cache = self.matcher.build_ingredient_index()

        for idx, seat in enumerate(seats, start=1):
            selected_dish = None
            selected_score = -1
            selected_issues: List[Dict[str, Any]] = []
            req = seat.get('require')
            hit_req = False

            # 席位按「本类型优先、备选类型兜底」取菜：
            # 先把本类型（如冷碟）能挑的挑完，挑不出来才退到备选类型（如素菜）。
            # 早先是把所有类型混成一个池子按分数统一排，结果素菜分高就把冷碟位占了，
            # 席单上「迎宾冷碟（三）」端的是炒青菜——席位名与出品对不上。
            for seat_type in seat['types']:
                candidates = self.matcher.get_seasonal_dishes(
                    solar_term, seat_type, main_constitution,
                    secondary_constitution, special_group, limit=40,
                    dish_types=[seat_type],
                )
                pool = [c for c in candidates if c[0].id not in used_dish_ids]
                safe = [c for c in pool if not self.validator.has_block(c[2])]
                pick_from = safe or pool

                # 席位硬要求：荤/素冷碟、五类食材、含药材的汤
                if pick_from and req:
                    wanted = [c for c in pick_from if tax.match_req(c[0], req)]
                    if wanted:
                        pick_from = wanted
                        hit_req = True
                if not pick_from:
                    continue
                # 主料去重：与已上桌的菜主料撞得越多，排位越靠后。
                # 家庭四道菜最容易撞主料（连出两道山药/两道鸡），这一步专治它。
                # 技法去重：八道热菜要蒸炖炒焖轮着来，同技法的往后排。
                # 蛋白去重：同一类（鱼/虾/鸡/牛）上第三次以后开始扣分，避免整桌重复。
                def _penalty(dish):
                    pen = 45 * len(self._main_keys(dish) & used_main_keys)
                    if tax.method_of(dish) in used_methods:
                        pen += 25
                    for tg in tax.protein_tags(dish):
                        if tg != 'veg':
                            pen += 15 * min(tag_used.get(tg, 0), 3)
                    # 药膳汤要「标得出药材配伍与功效」：课件方子才写有功效，
                    # 资料包那些没记功效的往后排，实在没有才用，前端会如实标注。
                    if req == 'herb' and not getattr(dish, 'efficacy_chinese', None):
                        pen += 120
                    return pen

                pick_from = sorted(
                    pick_from,
                    key=lambda c: c[1] - _penalty(c[0]),
                    reverse=True,
                )
                # 近分轮换：分数差 50 以内的前 4 名按节气确定性轮换取一道。
                # 没有这步，评分高的永远是同一批课件菜，新补的菜单菜
                # （无功效记载、评分 0）永远上不了席，各节气席单也千篇一律。
                top = pick_from[:4]
                if len(top) > 1:
                    best = top[0][1]
                    near = [c for c in top if best - c[1] <= 50]
                    pick_idx = (solar_term.id * 7 + idx) % len(near)
                    selected_dish, selected_score, selected_issues = near[pick_idx]
                else:
                    selected_dish, selected_score, selected_issues = top[0]
                break

            if req and not hit_req:
                unmet.append({
                    'seat': seat['name'],
                    'require': req,
                    'label': seat.get('require_label', req),
                    'note': '菜谱库里没有符合条件的菜，本席位用其他菜顶上了。补一条菜谱即可满足。',
                })

            # 兜底：同类型实在没货，才退回库里任意一道没用过的菜，并在席位名上不撒谎
            if not selected_dish:
                fallback = self.db.query(Dish).filter(Dish.id.notin_(used_dish_ids)).first()
                if fallback:
                    selected_dish = fallback
                    selected_score = 10
                    selected_issues = self.validator.validate_dish(
                        fallback, ing_index_cache,
                        special_group or 'none',
                        main_constitution.name if main_constitution else None,
                    )

            if selected_dish:
                used_dish_ids.add(selected_dish.id)
                used_main_keys |= self._main_keys(selected_dish)
                used_methods.add(tax.method_of(selected_dish))
                for _t in tax.protein_tags(selected_dish):
                    if _t != 'veg':
                        tag_used[_t] = tag_used.get(_t, 0) + 1

                # 添加到购物清单
                if selected_dish.main_ingredients:
                    for ing in selected_dish.main_ingredients:
                        all_shopping_list.add(ing['name'])
                if selected_dish.medicinal_ingredients:
                    for ing in selected_dish.medicinal_ingredients:
                        all_shopping_list.add(ing['name'])
                
                # 生成匹配理由
                match_reason = self.matcher.get_match_reason(selected_dish, solar_term, main_constitution)
                
                warnings_str = [f"[{i['level']}] {i['type']}：{i['detail']}" for i in selected_issues]
                alerts = self.validator.to_alerts(selected_issues)

                # 食材展示串：主料 + 药材（带用量）
                ings_parts = []
                for field in ('main_ingredients', 'auxiliary_ingredients', 'medicinal_ingredients'):
                    for ing in (getattr(selected_dish, field, None) or []):
                        ings_parts.append(ing.get('name') + (' ' + ing.get('amount') if ing.get('amount') else ''))
                ing_index = ing_index_cache
                is_med = 0
                for field in ('main_ingredients', 'medicinal_ingredients'):
                    for ing in (getattr(selected_dish, field, None) or []):
                        obj = ing_index.get(ing.get('name'))
                        if obj is None:
                            continue
                        val = obj.get('is_medicinal') if isinstance(obj, dict) else getattr(obj, 'is_medicinal', None)
                        if val == 1 or val is True:
                            is_med = 1
                if getattr(selected_dish, 'is_medicinal', 0):
                    is_med = 1

                # 药膳汤要标明药材配伍与功效；茶饮要标明季节、功效与宜忌
                pairing = tax.herb_pairing(selected_dish) if seat['course'] == 'soup' else ''
                drink_note = ''
                if seat['course'] == 'drink':
                    parts = []
                    seasons = [s for s in (selected_dish.suitable_seasons or []) if s]
                    if seasons:
                        parts.append('适宜季节：' + '、'.join(seasons))
                    if selected_dish.efficacy_chinese:
                        parts.append('功效：' + selected_dish.efficacy_chinese)
                    if selected_dish.contraindication:
                        parts.append('饮用宜忌：' + selected_dish.contraindication)
                    drink_note = '；'.join(parts) or '该款茶饮未标注季节与宜忌，出品前请按体质核对'

                dish_item = BanquetDishItem(
                    position=idx,
                    position_name=seat['name'],
                    course=seat['course'],
                    course_name=self.COURSE_NAME.get(seat['course'], '菜品'),
                    dish=selected_dish,
                    match_reason=match_reason,
                    warnings=warnings_str,
                    alerts=alerts,
                    stat=self.validator.stat_of(selected_issues),
                    ingredients_text='、'.join(ings_parts) or '—',
                    is_medicinal=is_med,
                    require_label=seat.get('require_label', ''),
                    food_tag=tax.tag_label(selected_dish),
                    method=tax.method_of(selected_dish),
                    pairing=pairing,
                    drink_note=drink_note,
                )
                dishes.append(dish_item)
                safety_warnings.extend(warnings_str)
        
        # 生成设计理念
        season_principles = {
            '春': '春生养肝，助阳生发，少酸多甘，清淡升散',
            '夏': '夏长养心，清热解暑，生津止渴，忌过生冷',
            '长夏': '长夏健脾，祛湿化浊，芳香醒脾，清淡甘淡',
            '秋': '秋收润肺，滋阴润燥，少辛增酸，生津养肺',
            '冬': '冬藏补肾，温补阳气，填精补髓，温而不燥'
        }
        
        banquet_types_desc = {
            'family': '家庭餐桌口味适中、老少皆宜，讲究荤素搭配与家常可操作',
            'business': '商务宴请出品精致、搭配得体，兼顾养生与席面排场',
            'health': '养生主题宴，突出节气养生与体质调理，功效为先'
        }

        # 席面构成按实际席位统计（有几道冷菜、几道热菜……），不再写死数字
        course_stat: Dict[str, int] = {}
        for d in dishes:
            course_stat[d.course] = course_stat.get(d.course, 0) + 1
        course_text = '、'.join(
            f"{self.COURSE_NAME.get(k, '菜品')}{v}道"
            for k, v in course_stat.items()
        ) or '—'

        scene_desc = {
            'family': '本席为家常餐桌设计，四菜一汤一饮，两荤两素，一餐可做完。',
            'business': '本席为商务宴请设计，两道冷菜开席、四道热菜撑场面，一汤一饮收尾。',
            'health': '本席为养生宴设计：冷菜六道三荤三素、口味清爽，'
                      '热菜八道覆盖虾、鱼、牛羊猪、鸡、时蔬五类且蒸炖炒焖错开，'
                      '一道药膳汤标明药材配伍，点心或主食一道，季节茶饮收尾。'
        }

        design_concept = f"""本席为{solar_term.name}节气定制，遵循{season_principles.get(solar_term.season, '顺时养生')}总原则。\n针对{main_constitution.name}体质特点，{main_constitution.diet_principle}，"""
        if secondary_constitution:
            design_concept += f"兼顾{secondary_constitution.name}体质调理需求，"
        design_concept += f"{banquet_types_desc.get(banquet_type, '顺时养生')}。"
        design_concept += f"{scene_desc.get(banquet_type, '')}"
        design_concept += f"全席共{len(dishes)}道（{course_text}），按 {headcount} 人席设计，"
        design_concept += "冷热搭配、荤素均衡、性味平和，兼顾色、香、味、形、效五大出品标准。"
        if banquet_type == 'health' and used_methods:
            design_concept += f"热菜技法分布：{'、'.join(sorted(m for m in used_methods if m))}。"

        # 文化故事
        culture_story = solar_term.culture_story
        if solar_term.season == '春':
            culture_story += '\\n春季养生重在养肝，古人云：春三月，此谓发陈，天地俱生，万物以荣。本席选料以春季时令芽菜、绿叶菜为主，助阳气生发，疏肝理气。'
        elif solar_term.season == '夏':
            culture_story += '\\n夏季养生重在养心，夏三月，此谓蕃秀，天地气交，万物华实。本席清淡解暑，清热而不伤阳，利湿而不伤阴。'
        elif solar_term.season == '秋':
            culture_story += '\\n秋季养生重在润肺，秋三月，此谓容平，天气以急，地气以明。本席滋阴润燥，养肺生津，少辛增酸，应收敛之道。'
        elif solar_term.season == '冬':
            culture_story += '\\n冬季养生重在补肾，冬三月，此谓闭藏，水冰地坼，无扰乎阳。本席温补阳气，填精补髓，为来年春天储备能量。'
        
        # 时间安排建议：场景不同，备餐节奏完全不同，别再共用一套宴席时间线
        time_schedule_map = {
            'health': f"""10 人席出品时间安排建议（当前按 {headcount} 人席，人数变动作相应增减）：
1. 提前1天：干货泡发（银耳、莲子、药材等），高汤熬制，卤味入味
2. 提前4小时：药膳汤入锅慢炖，大件原料改刀腌味
3. 提前2小时：六道冷碟制作完成（三荤三素分盘摆好），封膜冷藏
4. 提前90分钟：虾馔、鱼馔、大菜的配料切配到位，测算 {headcount} 位份出品量
5. 开席前40分钟：扣肉/炖菜入锅，蒸菜上笼
6. 开席前15分钟：炒菜、时蔬大火快炒出锅
7. 席间节奏：六冷碟开席 → 药膳汤暖场 → 八大热菜依次为虾、鱼、畜、禽、时蔬逐级递进 → 点心/主食垫底 → 茶饮收尾""",
            'family': """家庭备餐时间安排建议：
1. 前一晚：干货泡发（银耳、莲子、薏米等），肉类解冻腌味
2. 餐前90分钟：例汤下锅，小火慢炖
3. 餐前40分钟：两道素菜洗切配好，两道热菜腌味上浆
4. 餐前15分钟：热菜先荤后素依次下锅，素菜大火快炒
5. 餐前5分钟：例汤调味出锅，饮品冲泡或温好
6. 上桌顺序：两荤两素同时上桌，例汤随餐，饮品餐后半小时饮用更养胃""",
            'business': """商务宴出品时间安排建议：
1. 提前1天：干货泡发、高汤熬制、冷菜原料预制
2. 提前3小时：例汤入锅慢炖，主菜腌味入味
3. 提前90分钟：两道冷菜制作完成，封膜冷藏
4. 提前40分钟：四道热菜配料切配到位，酱汁预调
5. 开席前20分钟：冷菜上桌摆盘，检查品相
6. 开席后：热菜按序出品，先清淡后浓郁，例汤中途上
7. 席间节奏：两冷菜开胃 → 四热菜递进 → 例汤暖场 → 佐餐饮品清口收尾""",
        }
        time_schedule = time_schedule_map.get(banquet_type, time_schedule_map['health'])

        # 添加免责声明
        safety_warnings.append(self.validator.get_disclaimer())
        
        # 去重安全警告
        safety_warnings = list(set(safety_warnings))
        
        # 全席分级统计：把各道菜的 block/warn/tip/good 累加
        total_stat = {'block': 0, 'warn': 0, 'tip': 0, 'good': 0}
        for d in dishes:
            for k in total_stat:
                total_stat[k] += (d.stat or {}).get(k, 0)

        # 疗程提示（Q3：胡老师 2026-09-23 核定 7 天为一疗程；间隔天数仍 pending）
        tc_rules = self.validator.rules.get('treatment_course') or {}
        tc_items = tc_rules.get('items') or []
        med_cnt = sum(1 for d in dishes if d.is_medicinal)
        tc_pick = None
        if tc_items:
            scope = 'medicated' if med_cnt > 0 else 'daily'
            tc_pick = next((x for x in tc_items if x.get('scope') == scope), tc_items[0])

        # 转换为schema模型
        return BanquetResponse(
            solar_term=SolarTermDetail.model_validate(solar_term),
            main_constitution=ConstitutionDetail.model_validate(main_constitution),
            secondary_constitution=ConstitutionDetail.model_validate(secondary_constitution) if secondary_constitution else None,
            special_group=special_group or 'none',
            banquet_type=banquet_type,
            banquet_scale=(banquet_scale if banquet_type == 'health' else 'standard') or 'standard',
            scene_name=self.SCENE_NAME.get(banquet_type, '养生宴'),
            structure_label=struct.get('label', ''),
            structure_text=course_text,
            course_stat=course_stat,
            headcount=headcount,
            unmet=unmet,
            design_concept=design_concept,
            culture_story=culture_story,
            dishes=dishes,
            shopping_list=list(all_shopping_list),
            time_schedule=time_schedule,
            safety_warnings=safety_warnings,
            stat=total_stat,
            group_name=self.validator.GROUP_NAME.get(special_group or 'none', '普通人群'),
            group_warning=self.validator.get_special_group_warning(special_group or 'none') or '',
            course_tip=(tc_pick or {}).get('advice', ''),
            course_pending=bool(tc_rules.get('pending')),
        )
