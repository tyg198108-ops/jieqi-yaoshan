# -*- coding: utf-8 -*-
"""把 dist 打成控制台可直接上传的 zip 包。

静态托管：解压后 index.html 必须在根层，不能有 web/ 这一层。
云函数：index.py 与 requirements.txt 必须在根层。
"""
import os, shutil, zipfile, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
OUT = os.path.join(os.path.dirname(ROOT), '腾讯云上传包')
if not os.path.isdir(OUT):
    os.makedirs(OUT)

def make(src, name, must):
    src = os.path.join(DIST, src)
    if not os.path.isdir(src):
        print('缺少目录：' + src); return None
    files = []
    for d, _, fs in os.walk(src):
        for f in fs:
            files.append(os.path.relpath(os.path.join(d, f), src).replace('\\', '/'))
    missing = [m for m in must if m not in files]
    if missing:
        print('[中止] %s 缺少必须文件：%s' % (name, '、'.join(missing))); return None
    dst = os.path.join(OUT, name)
    if os.path.exists(dst):
        os.remove(dst)
    z = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
    for rel in files:
        z.write(os.path.join(src, rel.replace('/', os.sep)), rel)
    z.close()
    print('%-28s %6.0f KB  %d 个文件' % (os.path.basename(dst), os.path.getsize(dst) / 1024, len(files)))
    return dst

print('输出目录：' + OUT + '\n')
a = make('web', '静态网站包.zip', ['index.html', 'app-data.js'])
b = make('cloudfunction', '云函数包.zip', ['index.py', 'requirements.txt'])
print()
if a and b:
    print('两个包都好了，去控制台上传即可。')
else:
    print('有包没打成，请先看上面的报错。')
