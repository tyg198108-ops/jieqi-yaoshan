from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class SolarTermBase(BaseModel):
    name: str
    season: str
    order: int
    
class SolarTermDetail(SolarTermBase):
    id: int
    english_name: Optional[str] = None
    date_range: str
    climate_features: str
    corresponding_organ: str
    health_principle: str
    suitable_foods: List[str]
    avoid_foods: List[str]
    recommended_ingredients: List[str]
    seasonal_ingredients: List[str]
    culture_story: str
    diet_notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class ConstitutionBase(BaseModel):
    name: str
    code: str
    
class ConstitutionDetail(ConstitutionBase):
    id: int
    overall_feature: str
    common_symptoms: List[str]
    tongue_feature: str
    disease_tendency: str
    diet_principle: str
    recommended_ingredients: List[str]
    avoid_ingredients: List[str]
    recommended_dishes: List[str]
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class IngredientBase(BaseModel):
    name: str
    category: str
    
class IngredientDetail(IngredientBase):
    id: int
    alias: Optional[str] = None
    # 说明：53 种普通食材（鲈鱼、莲藕、调味品等）的性味归经尚未补录，
    # 一律留空标 pending，不做编造。因此这些字段必须允许 None，
    # 否则 /api/ingredients 会直接 500（ResponseValidationError）。
    four_natures: Optional[str] = None
    five_flavors: Optional[List[str]] = None
    meridian_tropism: Optional[List[str]] = None
    efficacy_chinese: Optional[str] = None
    nutrition_info: Optional[str] = None
    suitable_seasons: Optional[List[str]] = None
    suitable_constitutions: Optional[List[str]] = None
    contraindication: Optional[str] = None
    dosage: Optional[str] = None
    cooking_methods: Optional[List[str]] = None
    good_combinations: Optional[List[str]] = None
    bad_combinations: Optional[List[str]] = None
    in_catalog: Optional[int] = None
    description: Optional[str] = None
    is_medicinal: Optional[int] = None
    source_lesson: Optional[str] = None
    source: Optional[str] = None
    catalog_note: Optional[str] = None
    catalog_confirmed: Optional[int] = None
    catalog_batch: Optional[str] = None
    catalog_official: Optional[str] = None
    pending_fields: Optional[List[str]] = None
    category_source: Optional[str] = None

    class Config:
        from_attributes = True

class DishBase(BaseModel):
    name: str
    category: str
    dish_type: str
    
class DishDetail(DishBase):
    id: int
    main_ingredients: List[Any]
    auxiliary_ingredients: Optional[List[Any]] = None
    medicinal_ingredients: Optional[List[Any]] = None
    # 资料包菜谱只给了「菜名/食材/做法/搭配定位」，功效、口味、出品标准一律没有。
    # 这些字段若维持必填，新菜一进来接口就 500，因此放宽为可选。
    cooking_method: Optional[str] = None
    cooking_steps: Optional[List[str]] = None
    skills: Optional[str] = None
    efficacy_chinese: Optional[str] = None
    nutrition_info: Optional[str] = None
    suitable_constitutions: Optional[List[str]] = None
    suitable_seasons: Optional[List[str]] = None
    contraindication: Optional[str] = None
    appearance_standard: Optional[str] = None
    flavor: Optional[str] = None
    is_medicinal: Optional[int] = None
    story: Optional[str] = None
    derived_fields: Optional[List[str]] = None
    derived_from: Optional[str] = None
    description: Optional[str] = None
    source_lesson: Optional[str] = None
    source: Optional[str] = None
    
    class Config:
        from_attributes = True

class BanquetGenerateRequest(BaseModel):
    solar_term_id: int
    main_constitution_id: int
    secondary_constitution_id: Optional[int] = None
    special_group: Optional[str] = None  # pregnant/children/elderly/none
    banquet_type: str = "health"  # health 养生宴 / family 家庭餐 / business 商务餐
    banquet_scale: Optional[str] = None
    flavor_preference: Optional[str] = None
    # 宴席人数，默认 10 人席
    headcount: int = 10
    # 养生宴收尾一道：dessert 药膳点心 / staple 养生主食（二选一）
    finale: Optional[str] = 'dessert'

class BanquetDishItem(BaseModel):
    position: int
    position_name: str
    # 上菜分组：cold 冷菜 / hot 热菜 / veg 素菜 / soup 汤品 / staple 主食 / dessert 羹品甜品 / drink 饮品
    course: str = 'hot'
    course_name: str = '热菜'
    # 席位硬要求标注 + 菜的食材类别 / 出品技法（用来核验「五类必覆、技法多样」）
    require_label: str = ''
    food_tag: str = ''
    method: str = ''
    # 药膳汤的药材配伍；茶饮的适宜季节 / 功效 / 饮用宜忌
    pairing: str = ''
    drink_note: str = ''
    dish: DishDetail
    match_reason: str
    warnings: List[str] = []
    # 结构化分级告警（前端直接渲染）：level block/warn/tip/good + icon + msg + 出处 + 推断标记
    alerts: List[Dict[str, Any]] = []
    stat: Dict[str, int] = {}
    ingredients_text: str = ''
    is_medicinal: int = 0

class BanquetResponse(BaseModel):
    solar_term: SolarTermDetail
    main_constitution: ConstitutionDetail
    secondary_constitution: Optional[ConstitutionDetail] = None
    special_group: str
    banquet_type: str
    banquet_scale: str = 'standard'
    scene_name: str = '养生宴'
    structure_label: str = ''          # 席面名，如「养生正席」「四菜一汤一饮」
    structure_text: str = ''           # 构成说明，如「迎宾冷菜3道、热菜5道…」
    course_stat: Dict[str, int] = {}   # 各分组道数，前端按此出小标题
    headcount: int = 10                # 宴席人数
    unmet: List[Dict[str, str]] = []   # 未满足的席位要求，如实上报，不硬凑
    design_concept: str
    culture_story: str
    dishes: List[BanquetDishItem]
    shopping_list: List[str]
    time_schedule: str
    safety_warnings: List[str] = []
    # 新增：全席统计与疗程 / 人群提示（前端分级汇总与疗程条）
    stat: Dict[str, int] = {}
    group_name: str = '普通人群'
    group_warning: str = ''
    course_tip: str = ''
    course_pending: bool = False
