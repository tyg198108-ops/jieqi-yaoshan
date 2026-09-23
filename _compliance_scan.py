# -*- coding: utf-8 -*-
"""合规扫描：健康类内容不得出现医疗宣称，也不得声称能治病。

为什么需要：面向公众的健康内容里，出现"治疗/治愈/疗效"这类词，
轻则被平台下架，重则按《广告法》第十七条认定为你我させての医疗断言。
规则引擎内部的分级（block/warn/tip）是风险提示，不等于对外疗效宣称，两部分要分开看。

扫描范围：
  1. 前端可展示文案（index.html / js / css）
  2. 后端会输出给用户看的文案（engine、api 里的字符串常量）
  3. 数据文件里会展示给用户的字段（功效、宜忌、设计理念等）

用法： python _compliance_scan.py
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# 我会把这些词撕掉ׅ —— 只是它们在里有两类合法用法，扫描时要跳过：
#   1) 否定式：「不能替代药物治疗」「不构成医疗治疗建议」——这正是免责声明该说的话
#   2) 自引用：rules.json 里的 banned_words 清单本身，是我们用来过滤的词表
HARD = ['治愈', '根治', '主治', '治病', '医治', '疗效', '适应症', '特效', '抗癌',
        '治疗', '药用价值']
NEGATION = ('不能', '不会', '不可', '并非', '不是', '禁用', '违禁', '避免', '不得',
            '请勿', '拒绝', '替代药物', '不构成', '清单', 'banned', '封禁')
# 二类词:高风险语境才需要处理，先列出来人工确认
SOFT = ['药用', '疗程', '药方', '处方', '药品', '消炎']

# 这些字段会出现在页面上
DATA_TEXT_FIELDS = [
    'efficacy', 'efficacy_chinese', 'description', 'function', 'indications',
    'precautions', 'taboo', 'note', 'usage', 'dosage', 'design_concept',
    'health_principle', 'Diet_principle', 'diet_principle', 'concept',
    'overall_feature', 'disease_tendency'
]


def scan_text_files():
    hits = []
    targets = [ROOT]
    for base in ('js', 'css'):
        p = os.path.join(ROOT, base)
        if os.path.isdir(p):
            targets.append(p)
    targets.append(os.path.join(ROOT, 'backend'))
    targets.append(os.path.join(ROOT, 'backend', 'engine'))
    targets.append(os.path.join(ROOT, 'backend', 'api'))

    for base in targets:
        for f in sorted(os.listdir(base)):
            fp = os.path.join(base, f)
            if not os.path.isfile(fp):
                continue
            # 跳过生成产物：app-data.js 是 rules.json 的镜像，源头已在 [2] 里扫过了
            if f in ('app-data.js', 'app-data.js.bak'):
                continue
            if f.endswith(('.js', '.css', '.html', '.py')) and not f.startswith('_') and '.bak' not in f:
                try:
                    s = io.open(fp, encoding='utf-8').read()
                except Exception:
                    continue
                for w in HARD:
                    for m in re.finditer(re.escape(w), s):
                        # 否定式用法（免责声明）不算违规
                        head = s[max(0, m.start() - 24):m.start()]
                        if any(n in head for n in NEGATION):
                            continue
                        ln = s[:m.start()].count('\n') + 1
                        ctx = s[max(0, m.start() - 40):m.start() + 40].replace('\n', ' ')
                        hits.append((os.path.relpath(fp, ROOT), ln, w, ctx))
    return hits


def scan_data_fields():
    """扫描 JSON 里会展示给用户的文本字段。"""
    hits = []
    data_dir = os.path.join(ROOT, 'backend', 'data')
    for f in sorted(os.listdir(data_dir)):
        if not f.endswith('.json') or '.bak' in f:
            continue
        fp = os.path.join(data_dir, f)
        try:
            obj = json.loads(io.open(fp, encoding='utf-8').read())
        except Exception as e:
            print('  跳过（解析失败）%s: %s' % (f, e))
            continue

        # 自引用节点：banned_words 清单本身就是词表，不该被判为违规
        SELF_REF = {'banned_words', 'banned_words_by_type', 'laws', 'allowed_words'}

        def walk(node, path, key=None):
            if isinstance(node, dict):
                if node.get('_id'):
                    path = path + '/' + str(node.get('name') or node.get('id') or '?')
                for k, v in node.items():
                    if k in SELF_REF:
                        continue
                    nxt = '%s.%s' % (path.split('/')[-1], k)
                    if isinstance(v, str) and (k in DATA_TEXT_FIELDS or k.endswith('_chinese')):
                        for w in HARD:
                            if w in v and not any(n in v for n in NEGATION):
                                hits.append((f, path.split('/')[-1], w, v[:80]))
                    else:
                        walk(v, path + '/' + nxt, k)
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, path, key)

        walk(obj, f)
    return hits


def main():
    print('合规扫描：健康类内容的医疗宣称词\n' + '=' * 60)

    code_hits = scan_text_files()
    print('\n[1] 代码/页面文案：%d 处' % len(code_hits))
    for fp, ln, w, ctx in code_hits[:40]:
        print('  %-28s L%-5d [%s] …%s…' % (fp, ln, w, ctx))

    data_hits = scan_data_fields()
    print('\n[2] 数据文件展示字段：%d 处' % len(data_hits))
    seen = set()
    for fp, who, w, ctx in data_hits:
        key = (fp, w, ctx[:40])
        if key in seen:
            continue
        seen.add(key)
        print('  %-24s %-20s [%s] %s' % (fp, who[:20], w, ctx))

    total = len(code_hits) + len(data_hits)
    print('\n' + '=' * 60)
    if total == 0:
        print('✅ 未发现医疗宣称词')
    else:
        print('⚠️ 共 %d 处需处理（上面列出前若干）' % total)
    return total


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
