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

def _error_response(stage, exc):
    """把启动/调用期错误转成 500 JSON 返回。

    为什么必须做：云函数在 import 阶段崩溃时，网关只会给出笼统的
    FUNCTIONS_INVOCATION_FAILED，远程排查等于瞎子摸象；把堆栈尾部直接
    放进响应体，curl 一下就能看到缺了哪个包。
    """
    import traceback, json
    tb = traceback.format_exc().strip().splitlines()[-12:]
    body = json.dumps({
        'detail': 'yaoshan-api %s 阶段错误: %s' % (stage, type(exc).__name__),
        'error': str(exc)[:300],
        'traceback_tail': tb,
    }, ensure_ascii=False)
    return {
        'statusCode': 500,
        'headers': {'Content-Type': 'application/json; charset=utf-8'},
        'isBase64Encoded': False,
        'body': body,
    }


try:
    from cloud_adapter import handle  # noqa: E402
    from main import app  # noqa: E402
    _IMPORT_OK = True
except Exception as _e:  # 缺依赖/路径问题时函数仍可部署，但每个请求返回诊断信息
    _IMPORT_OK = False
    _IMPORT_ERR = _e
    handle = None
    app = None


def main(event, context=None):
    """云函数唯一入口。参数顺序和返回结构是网关规定的，不要改签名。"""
    if not _IMPORT_OK:
        return _error_response('启动(import)', _IMPORT_ERR)
    # 网关健康检查有时会带空 event，兜住避免 500
    if not event or not isinstance(event, dict):
        event = {'httpMethod': 'GET', 'path': '/api/health', 'headers': {}, 'queryString': ''}
    try:
        return handle(app, event)
    except Exception as e:
        return _error_response('调用', e)


if __name__ == '__main__':
    # 本地自测：python index.py
    print(main({
        'httpMethod': 'GET',
        'path': '/api/health',
        'headers': {'host': 'localhost'},
        'queryString': '',
        'body': None,
    }))
