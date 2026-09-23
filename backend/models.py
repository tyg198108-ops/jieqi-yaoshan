from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class SolarTerm(Base):
    __tablename__ = "solar_terms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, index=True, comment="节气名称")
    english_name = Column(String(50), comment="英文名")
    season = Column(String(20), comment="所属季节:春/夏/长夏/秋/冬")
    order = Column(Integer, comment="顺序1-24")
    date_range = Column(String(50), comment="时间范围")
    climate_features = Column(Text, comment="气候特点")
    corresponding_organ = Column(String(50), comment="对应脏腑")
    health_principle = Column(Text, comment="养生原则")
    suitable_foods = Column(JSON, comment="宜吃食材列表")
    avoid_foods = Column(JSON, comment="忌吃食材列表")
    recommended_ingredients = Column(JSON, comment="推荐核心食材")
    seasonal_ingredients = Column(JSON, comment="当季时令食材")
    culture_story = Column(Text, comment="民俗文化背景")
    diet_notes = Column(Text, comment="饮食注意事项")

class Constitution(Base):
    __tablename__ = "constitutions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, index=True, comment="体质名称")
    code = Column(String(20), unique=True, comment="代码")
    overall_feature = Column(Text, comment="总体特征")
    common_symptoms = Column(JSON, comment="常见表现列表")
    tongue_feature = Column(String(100), comment="舌象特征")
    disease_tendency = Column(Text, comment="发病倾向")
    diet_principle = Column(Text, comment="食疗原则")
    recommended_ingredients = Column(JSON, comment="推荐食材")
    avoid_ingredients = Column(JSON, comment="禁忌/慎用食材")
    recommended_dishes = Column(JSON, comment="推荐药膳类型")
    description = Column(Text, comment="详细描述")

class ConstitutionQuestion(Base):
    __tablename__ = "constitution_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    constitution_id = Column(Integer, ForeignKey("constitutions.id"), comment="对应体质ID")
    question_text = Column(String(200), comment="题目内容")
    options = Column(JSON, comment="选项及分值: [{text: '选项', score: 分值}]")
    constitution = relationship("Constitution")

class Ingredient(Base):
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, comment="食材名称")
    alias = Column(String(100), comment="别名")
    category = Column(String(30), comment="分类:补气类/补血类/滋阴类/壮阳类/理气类/活血类/清热类/祛湿类/安神类/健脾类/润肺类")
    four_natures = Column(String(10), comment="四气:寒/凉/平/温/热")
    five_flavors = Column(JSON, comment="五味:辛/甘/酸/苦/咸/淡/涩")
    meridian_tropism = Column(JSON, comment="归经")
    efficacy_chinese = Column(Text, comment="中医功效概要（食养层面，不作医疗宣称）")
    nutrition_info = Column(Text, comment="现代营养特点")
    suitable_seasons = Column(JSON, comment="适用季节/节气")
    suitable_constitutions = Column(JSON, comment="适用体质")
    contraindication = Column(Text, comment="禁忌人群/情况")
    dosage = Column(String(50), comment="常用剂量")
    cooking_methods = Column(JSON, comment="适合烹饪方法")
    good_combinations = Column(JSON, comment="经典搭配")
    bad_combinations = Column(JSON, comment="相反/相恶食材")
    # 注意：default 不能用 1。SQLAlchemy 遇到显式 None 会拿列默认值顶上，
    # 导致普通食材（普通食品，不适用药食同源目录）被写成"在目录内"。
    # 这里 default=None 表示"未标注"，语义才对。
    in_catalog = Column(Integer, default=None, comment="是否在药食同源目录:1是0否NULL=未标注/不适用")
    description = Column(Text, comment="详细说明")
    is_medicinal = Column(Integer, default=0, comment="是否按药材对待(风控属性):1是0否。注意与 in_catalog 是两回事：in_catalog 决定能不能卖，is_medicinal 决定要不要参与配伍校验")
    source_lesson = Column(String(50), comment="出处课节，如 第05课 P11")
    source = Column(String(20), default="legacy", comment="数据来源:course=课件台账 / legacy=原始数据")
    catalog_note = Column(Text, comment="目录归属说明")
    catalog_confirmed = Column(Integer, default=0, comment="目录归属是否经胡老师确认:1已确认0待定")
    catalog_batch = Column(String(80), comment="食药物质目录批次，如「2023 年第 9 号公告新增 9 种」")
    catalog_official = Column(String(80), comment="目录中的官方名称，如「枣（大枣、酸枣、黑枣）」")
    pending_fields = Column(JSON, comment="待补录字段列表：课件/资料没记载的一律留空，不臆造")
    category_source = Column(String(80), comment="分类出处；中药学常规分类需标注待课件核对")

class Dish(Base):
    __tablename__ = "dishes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, comment="菜品名称")
    category = Column(String(50), comment="功效分类")
    dish_type = Column(String(30), comment="菜品类型:冷碟/汤品/热菜/主菜/素菜/主食/甜品/茶饮")
    main_ingredients = Column(JSON, comment="主料[{name:名称, amount:用量}]")
    auxiliary_ingredients = Column(JSON, comment="辅料")
    medicinal_ingredients = Column(JSON, comment="药食同源食材及用量")
    cooking_method = Column(String(30), comment="烹饪技法")
    cooking_steps = Column(JSON, comment="制作步骤列表")
    skills = Column(Text, comment="刀工/火候/调味要点")
    efficacy_chinese = Column(Text, comment="中医功效说明")
    nutrition_info = Column(Text, comment="营养学说明")
    suitable_constitutions = Column(JSON, comment="适用体质列表")
    suitable_seasons = Column(JSON, comment="适用季节/节气")
    contraindication = Column(Text, comment="禁忌人群")
    appearance_standard = Column(Text, comment="出品标准:色/香/味/形")
    flavor = Column(String(30), comment="口味:清淡/浓郁/麻辣/鲜甜等")
    is_medicinal = Column(Integer, default=0, comment="是否为核心药膳主菜")
    story = Column(Text, comment="菜品文化故事")
    derived_fields = Column(JSON, comment="由食材数据推导而来的字段（非原文记载），如 suitable_constitutions")
    derived_from = Column(Text, comment="推导依据说明")
    description = Column(Text, comment="菜品说明/定位")
    source_lesson = Column(String(50), comment="出处课节，如 第12课 P5")
    source = Column(String(60), default="legacy", comment="数据来源：course=课件 / 资料包 V1.0 / legacy")
