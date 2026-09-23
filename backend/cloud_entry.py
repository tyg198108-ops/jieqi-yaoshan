"""云函数入口。

部署时本文件会被构建脚本复制为 `index.py`（云函数 handler 格式 index.main），
放在含 requirements.txt 的根目录。

环境变量（在云函数控制台或 cloudbaserc.json 里配）：
  YS_API_ONLY=1        只暴露 /api/*，不挂静态资源
  YS_DB_PATH=/tmp/yaoshan.db   代码目录只读，数据库必须落在 /tmp
  YS_VERSION           版本号，用于核对线上跑的是不是预期的代码
"""
import os
import sys
import importlib

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
    import traceback
    import json
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


# 模块名 → PyPI 分布名（少数对不上的）
_ALIAS = {'PIL': 'pillow', 'yaml': 'pyyaml', 'cv2': 'opencv-python',
          'dotenv': 'python-dotenv', 'sklearn': 'scikit-learn'}
_PIP_TARGET = '/tmp/ys_pip'      # 云函数代码目录只读，只有 /tmp 可写


def _autofix(exc):
    """缺包自愈：把缺失的包装到 /tmp 并重新 import。

    为什么要做：依赖是本机按 Linux/py3.9 预下载后打进 zip 的，
    漏掉任何一个传递依赖都会让函数在 import 期直接崩溃，
    补一个包就得重打 7MB 的包再上传一遍，来回成本很高。
    这里让函数自己去 PyPI 取，成功就重试一次，失败照常返回原错误。
    只在 ModuleNotFoundError 时触发，正常路径零开销。
    """
    if not isinstance(exc, ModuleNotFoundError):
        return False
    mod = (exc.name or '').split('.')[0]
    if not mod or mod.startswith('_') or mod in sys.builtin_module_names:
        return False
    try:
        import subprocess
        cmd = [sys.executable, '-m', 'pip', 'install', '-q', '--disable-pip-version-check',
               '-t', _PIP_TARGET, '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple',
               '--timeout', '20', _ALIAS.get(mod, mod)]
        rc = subprocess.call(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, timeout=75)
        if rc != 0:
            return False
        if _PIP_TARGET not in sys.path:
            sys.path.insert(0, _PIP_TARGET)
        importlib.invalidate_caches()
        return True
    except Exception:
        return False


def _load():
    """加载应用；缺包则自愈后重试一次。返回 None 表示成功。"""
    global handle, app
    try:
        from cloud_adapter import handle as _h
        from main import app as _a
        handle, app = _h, _a
        return None
    except Exception as e:
        if not _autofix(e):
            return e
    try:
        from cloud_adapter import handle as _h
        from main import app as _a
        handle, app = _h, _a
        return None
    except Exception as e:
        return e


_IMPORT_ERR = _load()
_IMPORT_OK = _IMPORT_ERR is None
if not _IMPORT_OK:
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
