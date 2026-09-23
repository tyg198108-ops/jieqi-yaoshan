# -*- coding: utf-8 -*-
"""构建部署产物到 dist/。

为什么要有这一步：云函数和静态托管要求的目录结构跟开发目录不一样。
  dist/cloudfunction/   云函数包，必须自带 requirements.txt 和入口 index.py
  dist/web/             纯前端静态文件，不能带后端代码和数据库

运行： python _build_cloud.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, 'backend')
DIST = os.path.join(ROOT, 'dist')
FN = os.path.join(DIST, 'cloudfunction')
WEB = os.path.join(DIST, 'web')

# 以 _ 开头的是一次性数据清洗脚本（_p_catalog106.py 之类），不进云端包
SKIP_PY_PREFIX = ('_',)
SKIP_EXT = ('.bak', '.bak.cold', '.bak.fix', '.bak106', '.db', '.png', '.jpg', '.jpeg', '.md')
SKIP_DIRS = {'__pycache__', '.git', '.local_backup', 'dist', 'node_modules', '.pytest_cache'}


def _skip(name):
    return name.startswith('.') or name.endswith(SKIP_EXT) or name in SKIP_DIRS


def clean():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(FN, exist_ok=True)
    os.makedirs(WEB, exist_ok=True)


def copy_tree(src, dst, filter_fn=None):
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not _skip(d)]
        rel = os.path.relpath(root, src)
        target = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for f in files:
            if _skip(f):
                continue
            if filter_fn and not filter_fn(f, os.path.relpath(os.path.join(root, f), src)):
                continue
            shutil.copy2(os.path.join(root, f), os.path.join(target, f))
            n += 1
    return n


def build_function():
    # 后端 .py（排除一次性脚本；cloud_entry.py 已复制成 index.py，不要留重复入口）
    def keep_py(f, rel):
        return f.endswith('.py') and not f.startswith(SKIP_PY_PREFIX) and f != 'cloud_entry.py'
    n1 = copy_tree(BACKEND, FN, keep_py)

    # data/*.json —— 是运行时的事实源，云端首次冷启动要用它建库
    data_src = os.path.join(BACKEND, 'data')
    n2 = copy_tree(data_src, os.path.join(FN, 'data'),
                   lambda f, rel: f.endswith('.json'))

    # 入口与依赖清单
    shutil.copy2(os.path.join(BACKEND, 'cloud_entry.py'), os.path.join(FN, 'index.py'))
    shutil.copy2(os.path.join(BACKEND, 'requirements_cloud.txt'), os.path.join(FN, 'requirements.txt'))

    # 依赖直接打进包里（_cloud_deps 为 manylinux2014/py39 预下载产物，见 _get_deps 命令）。
    # 为什么不靠云端装：zip 上传的函数不保证触发在线安装依赖，缺包时表现是
    # FUNCTIONS_INVOCATION_FAILED，远程很难排查；自带依赖一次解决。
    n3 = 0
    deps = os.path.join(ROOT, '_cloud_deps')
    if os.path.isdir(deps):
        def keep_dep(f, rel):
            r = rel.replace('\\', '/')
            return not (f.endswith(('.pyc', '.whl')) or '__pycache__' in r
                        or r.startswith('bin/') or r.startswith('include/')
                        or '/bin/' in r or '/include/' in r)
        n3 = copy_tree(deps, FN, keep_dep)
    print(f'  云函数：{n1} 个 py + {n2} 个 json + index.py + requirements.txt + {n3} 个依赖文件')
    return n1 + n2 + n3


def build_web():
    for name in ('index.html', 'app-data.js'):
        shutil.copy2(os.path.join(ROOT, name), os.path.join(WEB, name))
    n = 2
    for sub in ('js', 'css', 'vendor'):
        n += copy_tree(os.path.join(ROOT, sub), os.path.join(WEB, sub))
    print(f'  静态站：{n} 个文件（含 js/css/vendor）')
    return n


def sync_frontend():
    """发布前把 data/*.json 同步成 app-data.js。

    不同步的后果很难查：线上静态托管在后端不可达时会降级读本地副本，
    副本里是几周前的旧数据，用户看到的结果跟真实引擎不一致。
    """
    print('  同步 app-data.js …')
    subprocess.check_call([sys.executable, os.path.join(ROOT, '_sync_frontend.py')],
                          stdout=subprocess.DEVNULL)


def report():
    def size(p):
        total = 0
        for root, _, files in os.walk(p):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total

    print('\n产物清单：')
    print(f'  dist/cloudfunction  {size(FN) / 1024:.0f} KB')
    print(f'  dist/web            {size(WEB) / 1024 / 1024:.2f} MB')

    # 安全检查：静态站里绝不能出现后端代码和数据库
    bad = []
    for root, _, files in os.walk(WEB):
        for f in files:
            if f.endswith(('.py', '.db', '.json')) and f != 'package.json':
                bad.append(os.path.join(root, f))
    if bad:
        print('\n[警告] 静态目录里混入了后端文件（应排查）：')
        for b in bad[:5]:
            print('   ', b)
    else:
        print('  安全检查通过：dist/web 无后端源码与数据库')


def main():
    print('构建部署产物 …')
    clean()
    sync_frontend()
    build_function()
    build_web()
    report()
    print('\n下一步：')
    print('  tcb fn deploy yaoshan-api -e jieqi-yaoshan-d7gd6ypfscd10299f')
    print('  tcb hosting deploy dist/web -e jieqi-yaoshan-d7gd6ypfscd10299f')


if __name__ == '__main__':
    main()
