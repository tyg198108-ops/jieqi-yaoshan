# -*- coding: utf-8 -*-
"""P1-2 补 24 节气英文名（中国官方/UNESCO 通用译名）"""
import json

EN = {
    "立春": "Start of Spring",
    "雨水": "Rain Water",
    "惊蛰": "Awakening of Insects",
    "春分": "Spring Equinox",
    "清明": "Pure Brightness",
    "谷雨": "Grain Rain",
    "立夏": "Start of Summer",
    "小满": "Grain Buds",
    "芒种": "Grain in Ear",
    "夏至": "Summer Solstice",
    "小暑": "Minor Heat",
    "大暑": "Major Heat",
    "立秋": "Start of Autumn",
    "处暑": "End of Heat",
    "白露": "White Dew",
    "秋分": "Autumn Equinox",
    "寒露": "Cold Dew",
    "霜降": "Frost's Descent",
    "立冬": "Start of Winter",
    "小雪": "Minor Snow",
    "大雪": "Major Snow",
    "冬至": "Winter Solstice",
    "小寒": "Minor Cold",
    "大寒": "Major Cold",
}

p = "backend/data/solar_terms.json"
d = json.load(open(p, encoding="utf-8"))
n = 0
for s in d:
    s.setdefault("english_name_source", "通用官方译名（UNESCO 二十四节气英译）")
    if not s.get("english_name") and s["name"] in EN:
        s["english_name"] = EN[s["name"]]
        n += 1
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("filled:", n)
print("remain empty:", sum(1 for s in d if not s.get("english_name")))
print([s["english_name"] for s in d])
