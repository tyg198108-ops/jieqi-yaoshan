"""数据库自举：保证 engine 里的表存在且有数据。

为什么要这个模块
================
本地开发时数据库由 `python init_db.py` 从 data/*.json 生成，改了 JSON 忘了重建，
页面就会读到旧数据 —— 这个坑在项目里出现过。

云函数环境更麻烦：只有 /tmp 可写，实例冷启动后 /tmp 是空的，数据库必然不存在。
所以把「表不存在或没数据就自动从 JSON 灌一遍」做成能力，本地和云端走同一条路：

    本地：YS_DB_PATH 未设 → 用 backend/yaoshan.db，有数据就跳过，没数据就灌
    云端：YS_DB_PATH=/tmp/yaoshan.db → 冷启动必定触发一次灌数据

环境变量
========
YS_DB_PATH      数据库文件路径（默认 backend/yaoshan.db）
YS_DB_REBUILD=1 强制重建（改了 data/*.json 之后用它，本地开发常用）
"""
import os
import threading

from sqlalchemy import inspect

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(_HERE, 'yaoshan.db')

_lock = threading.Lock()


def db_path():
    return os.environ.get('YS_DB_PATH') or DEFAULT_DB_PATH


def needs_data(engine):
    """缺表或核心表没数据都算需要重建。"""
    insp = inspect(engine)
    for table in ('solar_terms', 'constitutions', 'ingredients', 'dishes'):
        if not insp.has_table(table):
            return True
    return False


def build_from_json(verbose=False):
    """从 data/*.json 全量重建。init_db.py 与云端冷启动共用这一份逻辑。"""
    import json

    # 延迟导入：models → database，避免在 database 还没初始化完时被反向导入
    from database import Base, engine, SessionLocal
    from models import SolarTerm, Constitution, ConstitutionQuestion, Ingredient, Dish

    def build(model, payload):
        """用 JSON 构造 ORM 对象，自动丢掉模型里不存在的字段。

        数据清洗脚本给 JSON 加新字段（is_medicinal / source_lesson 等）时，
        如果忘了同步 models.py，直接 **payload 会抛 TypeError。这里做白名单过滤。
        """
        cols = {c.name for c in model.__table__.columns}
        dropped = [k for k in payload if k not in cols]
        if dropped and verbose:
            print(f'  [db] {model.__name__} 忽略未映射字段: {dropped}')
        return model(**{k: v for k, v in payload.items() if k in cols})

    data_dir = os.path.join(_HERE, 'data')

    def load(name):
        with open(os.path.join(data_dir, name), 'r', encoding='utf-8') as f:
            return json.load(f)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for m in (SolarTerm, Constitution, ConstitutionQuestion, Ingredient, Dish):
            db.query(m).delete()
        db.commit()

        solar_terms = load('solar_terms.json')
        constitutions = load('constitutions.json')
        questions = load('constitution_questions.json')
        ingredients = load('ingredients.json')
        dishes = load('dishes.json')

        for st in solar_terms:
            db.add(build(SolarTerm, st))
        for c in constitutions:
            db.add(build(Constitution, c))
        for q in questions:
            db.add(ConstitutionQuestion(**{
                k: v for k, v in q.items()
                if k in {c.name for c in ConstitutionQuestion.__table__.columns}
            }))
        for ing in ingredients:
            db.add(build(Ingredient, ing))
        for d in dishes:
            db.add(build(Dish, d))
        db.commit()

        if verbose:
            print('数据库初始化完成！')
            print(f'  节气 {len(solar_terms)} / 体质 {len(constitutions)} / 测试题 {len(questions)}')
            print(f'  食材 {len(ingredients)} / 菜品 {len(dishes)}')
        return {
            'solar_terms': len(solar_terms), 'constitutions': len(constitutions),
            'questions': len(questions), 'ingredients': len(ingredients), 'dishes': len(dishes),
        }
    finally:
        db.close()


def bootstrap(verbose=None):
    """对外唯一入口。幂等 + 加锁，重复调用无害。"""
    from database import engine

    if verbose is None:
        verbose = bool(os.environ.get('YS_DB_VERBOSE'))
    force = os.environ.get('YS_DB_REBUILD') == '1'

    with _lock:
        if not force and not needs_data(engine):
            return None
        return build_from_json(verbose=verbose)


if __name__ == '__main__':
    print('当前数据库：', db_path())
    r = bootstrap(verbose=True)
    print('无需重建' if r is None else '已重建')
