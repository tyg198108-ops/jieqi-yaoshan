import json
import os
from database import Base, engine, SessionLocal
from models import SolarTerm, Constitution, ConstitutionQuestion, Ingredient, Dish


def build(model, payload):
    """
    用 JSON 构造 ORM 对象，自动丢掉模型里不存在的字段。

    为什么需要这个：数据清洗脚本往 JSON 里加新字段（is_medicinal / source_lesson /
    catalog_confirmed 等）时，如果忘了同步 models.py，直接 **payload 会抛
    TypeError: 'xxx' is an invalid keyword argument —— 这个坑已经踩了三次。
    这里统一做白名单过滤，加新字段不会再把 init_db 搞崩。
    """
    cols = {c.name for c in model.__table__.columns}
    dropped = [k for k in payload if k not in cols]
    if dropped:
        print(f'  [init_db] {model.__name__} 忽略未映射字段: {dropped}')
    return model(**{k: v for k, v in payload.items() if k in cols})


def init_db():
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 清空已有数据
    db.query(SolarTerm).delete()
    db.query(Constitution).delete()
    db.query(ConstitutionQuestion).delete()
    db.query(Ingredient).delete()
    db.query(Dish).delete()
    db.commit()
    
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
    # 导入节气数据
    with open(os.path.join(data_dir, 'solar_terms.json'), 'r', encoding='utf-8') as f:
        solar_terms = json.load(f)
        for st in solar_terms:
            db_st = build(SolarTerm, st)
            db.add(db_st)
    
    # 导入体质数据
    with open(os.path.join(data_dir, 'constitutions.json'), 'r', encoding='utf-8') as f:
        constitutions = json.load(f)
        for c in constitutions:
            db_c = build(Constitution, c)
            db.add(db_c)
    
    db.commit()
    
    # 导入体质测试题
    with open(os.path.join(data_dir, 'constitution_questions.json'), 'r', encoding='utf-8') as f:
        questions = json.load(f)
        for q in questions:
            db_q = ConstitutionQuestion(**q)
            db.add(db_q)
    
    # 导入食材数据
    with open(os.path.join(data_dir, 'ingredients.json'), 'r', encoding='utf-8') as f:
        ingredients = json.load(f)
        for ing in ingredients:
            db_ing = build(Ingredient, ing)
            db.add(db_ing)
    
    # 导入菜品数据
    with open(os.path.join(data_dir, 'dishes.json'), 'r', encoding='utf-8') as f:
        dishes = json.load(f)
        for d in dishes:
            db_d = build(Dish, d)
            db.add(db_d)
    
    db.commit()
    db.close()
    print("数据库初始化完成！")
    print(f"已导入 {len(solar_terms)} 个节气")
    print(f"已导入 {len(constitutions)} 种体质")
    print(f"已导入 {len(questions)} 道测试题")
    print(f"已导入 {len(ingredients)} 种食材")
    print(f"已导入 {len(dishes)} 道菜品")

if __name__ == '__main__':
    init_db()
