"""数据库引擎。

本地与云端共用一个文件，靠环境变量区分，避免维护两套配置：

  本地  YS_DB_PATH 不设 → backend/yaoshan.db（可写，常规 SQLite 行为）
  云端  YS_DB_PATH=/tmp/yaoshan.db → 唯一可写目录，缺失时由 db_bootstrap 自动灌数据

为什么云端要走 /tmp：云函数的代码目录是只读的，SQLite 打开时会尝试创建
-journal / -wal 临时文件，直接连打包进来的 db 会报 "attempt to write a
readonly database"。/tmp 是每个实例私有的临时空间，够用且不会串数据。
"""
import os
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(_HERE, 'yaoshan.db')

DB_PATH = os.environ.get('YS_DB_PATH') or DEFAULT_DB_PATH

# 父目录可能不存在（云函数冷启动时 /tmp 是干净的），先建出来
_db_dir = os.path.dirname(DB_PATH)
if _db_dir and not os.path.exists(_db_dir):
    try:
        os.makedirs(_db_dir, exist_ok=True)
    except OSError as e:
        logger.warning('无法创建数据库目录 %s：%s', _db_dir, e)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # 只读场景不需要等待锁，超时设短一点，卡住时能早点报错而不是一直挂
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _rec):
    """SQLite 性能三件套。数据量很小（200 食材 / 150 菜品），但对冷启动敏感的
    云函数环境来说，WAL + 内存临时表能省下几十毫秒。"""
    cur = dbapi_conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA temp_store=MEMORY")
    except Exception as e:  # pragma 失败不影响主流程
        logger.debug('设置 SQLite pragma 失败：%s', e)
    finally:
        cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
