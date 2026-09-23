"""云函数入口。

部署时本文件会被构建脚本复制为 `index.py`（云函数 handler 格式 index.main），
放在含 requirements.txt 的根目录，CloudBase CLI 上传后自动安装依赖。

环境变量（在云函数控制台或 cloudbaserc.json 里配）：
  YS_API_ONLY=1        只暴露 /api/*，不挂静态资源
  YS_DB_PATH=/tmp/yaoshan.db   代码目录只读，数据库必须落在 /tmp
  YS_VERSION           版本号，用于核对线上跑的是不是预期的代码
"""
import os

# 这两个必须在 import app 之前设置：main.py 在模块加载期就据此决定是否挂载静态资源、
# 数据库连接指向哪里。顺序写错会导致本地代码正常、线上却连错库。
os.environ.setdefault('YS_API_ONLY', '1')
os.environ.setdefault('YS_DB_PATH', '/tmp/yaoshan.db')

from cloud_adapter import handle  # noqa: E402
from main import app  # noqa: E402


def main(event, context=None):
    """云函数唯一入口。参数顺序和返回结构是网关规定的，不要改签名。"""
    # 网关健康检查有时会带空 event，兜住避免 500
    if not event or not isinstance(event, dict):
        event = {'httpMethod': 'GET', 'path': '/api/health', 'headers': {}, 'queryString': ''}
    try:
        return handle(app, event)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json; charset=utf-8'},
            'isBase64Encoded': False,
            'body': '{"detail":"云函数内部错误: %s"}' % type(e).__name__,
        }


if __name__ == '__main__':
    # 本地自测：python index.py
    print(main({
        'httpMethod': 'GET',
        'path': '/api/health',
        'headers': {'host': 'localhost'},
        'queryString': '',
        'body': None,
    }))
