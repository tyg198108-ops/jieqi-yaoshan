# -*- coding: utf-8 -*-
"""P1-1/P1-4 扫描：在课件与台账中检索缺失食材的性味/剂量线索，只输出候选，不自动写入"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "data")

CORPUS = []
for f in sorted(os.listdir(ROOT)):
    if f.endswith(".md") and ("演讲稿" in f or f.startswith("第")):
        CORPUS.append(os.path.join(ROOT, f))
LEDGER = os.path.join(ROOT, "_知识台账", "中医药膳营养师_知识点台账.md")
if os.path.exists(LEDGER):
    CORPUS.append(LEDGER)

DOCS = []
for p in CORPUS:
    try:
        DOCS.append((os.path.basename(p), open(p, encoding="utf-8").read()))
    except Exception as e:
        print("skip", p, e, file=sys.stderr)

ing = json.load(open(os.path.join(DATA, "ingredients.json"), encoding="utf-8"))
missing = [i["name"] for i in ing if not i.get("four_natures")]
print("缺失性味食材数:", len(missing))

KW = re.compile(r"性[温寒平凉热]|味[甘酸苦辛咸]|[温寒平凉热](?:性)?[，。、]|归[肺脾心肝肾胃大肠小肠膀胱三焦胆心包经]|归.{1,6}经|\d+\s*[-~]\s*\d+\s*g|\d+\s*g")

out = {}
hit = 0
for name in missing:
    lines = []
    for fn, txt in DOCS:
        for ln in txt.splitlines():
            if name in ln and KW.search(ln):
                lines.append({"file": fn, "line": ln.strip()[:160]})
    if lines:
        hit += 1
        out[name] = lines[:4]

print("课件中有线索的:", hit, "/", len(missing))
print(json.dumps(out, ensure_ascii=False, indent=1))
