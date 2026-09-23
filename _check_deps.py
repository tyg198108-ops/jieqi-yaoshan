# -*- coding: utf-8 -*-
"""云函数依赖完整性检查。

云函数环境是 Linux + Python 3.9（只读代码目录 + /tmp 可写），
如果某个传递依赖没打进包，import 阶段才会崩且堆栈不落日志，排查成本极高。
所以构建时先把所有 dist-info 的 Requires-Dist 按 py3.9 求值一遍，
缺失的在这里就报出来，而不是等到线上 FUNCTIONS_INVOCATION_FAILED。

用法：python _check_deps.py [--fix 时打印可直接复制的 pip 命令]
"""
import os
import sys
import posixpath

ROOT = os.path.dirname(os.path.abspath(__file__))
DEPS = os.path.join(ROOT, '_cloud_deps')
TOOLS = os.path.join(ROOT, '_tools_deps')
sys.path.insert(0, TOOLS)

from packaging.requirements import Requirement  # noqa: E402
from packaging.utils import canonicalize_name   # noqa: E402

PY = {'python_version': '3.9', 'python_full_version': '3.9.18',
      'sys_platform': 'linux', 'platform_system': 'Linux',
      'platform_machine': 'x86_64', 'os_name': 'posix',
      'implementation_name': 'cpython', 'extra': ''}


def installed():
    """返回 {(canonical_name, version)} 及 name->Version 映射"""
    got = {}
    for d in os.listdir(DEPS):
        if not d.endswith('.dist-info'):
            continue
        base = d[:-len('.dist-info')]
        if '-' not in base:
            continue
        name, _, ver = base.rpartition('-')
        got[canonicalize_name(name)] = ver
    return got


def module_present(req_name):
    """按常见 分布名→顶层模块名 的映射判断包体是否真的在目录里。"""
    cand = [req_name, req_name.replace('-', '_'), req_name.replace('-', '')]
    # 少见的 分布名≠模块名
    alias = {
        'python-multipart': ['multipart', 'python_multipart'],
        'python-dotenv': ['dotenv'],
        'pyyaml': ['yaml'],
        'markupsafe': ['markupsafe'],
        'jinja2': ['jinja2'],
        'typing-extensions': ['typing_extensions'],
        'exceptiongroup': ['exceptiongroup'],
        'sniffio': ['sniffio'],
        'annotated-types': ['annotated_types'],
        'typing-inspection': ['typing_inspection'],
    }
    for c in cand:
        if c in alias:
            cand.extend(alias[c])
    for c in cand:
        if os.path.isdir(os.path.join(DEPS, c)):
            return True
        if os.path.isfile(os.path.join(DEPS, c + '.py')):
            return True
    return False


def main():
    if not os.path.isdir(DEPS):
        print('未找到 _cloud_deps，先跑一遍 _build_cloud.py 的依赖预下载')
        return 2
    got = installed()
    missing_dist, missing_body = [], []
    checked = 0

    for d in sorted(os.listdir(DEPS)):
        if not d.endswith('.dist-info'):
            continue
        # 只读元数据头部：METADATA 后面的长描述里可能也含 "Requires-Dist:" 字样，
        # 全文件扫描既慢又会误判
        meta = os.path.join(DEPS, d, 'METADATA')
        if not os.path.isfile(meta):
            continue
        lines = []
        with open(meta, encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.strip() in ('', '\n'):
                    break
                if line.startswith(('Description-Content-Type', 'Description:',
                                    'License-File', 'License:')):
                    continue
                lines.append(line)
        for line in lines:
            if not line.startswith('Requires-Dist:'):
                continue
            raw = line.split(':', 1)[1].strip()
            if ';' in raw:
                raw, _, marker = raw.partition(';')
            else:
                marker = ''
            try:
                req = Requirement(raw.strip())
            except Exception:
                continue
            # extra 依赖不装（例如 fastapi[standard]）
            if req.marker is not None and not req.marker.evaluate(PY):
                continue
            if marker:
                try:
                    from packaging.markers import Marker
                    if not Marker(marker).evaluate(PY):
                        continue
                except Exception:
                    pass
            checked += 1
            cn = canonicalize_name(req.name)
            if cn not in got:
                missing_dist.append(d.split('-')[0] + ' -> ' + str(req))
            elif not module_present(cn):
                missing_body.append(cn)

    print('已解析依赖声明：%d 条' % checked)
    print('本地包总数：%d' % len(got))
    if missing_dist:
        print('\n[缺失·未安装] %d 条' % len(missing_dist))
        for m in sorted(set(missing_dist)):
            print('  ' + m)
    if missing_body:
        print('\n[缺失·包体不在目录] %d 条' % len(missing_body))
        for m in sorted(set(missing_body)):
            print('  ' + m)
    if not missing_dist and not missing_body:
        print('\n依赖完整性检查通过')
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
