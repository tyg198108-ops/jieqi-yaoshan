# -*- coding: utf-8 -*-
"""P1-3 规则库二次扩容：补入第14课慢病饮食指导（课件原文，非推断）"""
import json

p = "backend/data/rules.json"
d = json.load(open(p, encoding="utf-8"))

d["chronic_diet_guidance"] = {
    "_comment": "常见慢病饮食指导，课件原文摘录。仅作「宜食推荐 + 忌口原则」提示（tip 级），不构成治疗建议",
    "_source_lesson": "第14课 P14",
    "高血压": {
        "name": "高血压",
        "principle": "低盐·低脂·多吃钾丰富的食物",
        "recommended": ["芹菜", "木耳", "海带", "山楂", "菊花茶"],
        "avoid": ["高盐腌制食品", "动物内脏", "浓肉汤"],
        "note": "钾有助于钠的排出，对控压有帮助",
        "source_lesson": "第14课 P14",
    },
    "糖尿病": {
        "name": "糖尿病",
        "principle": "控制总能量·选低 GI 食物·定时定量",
        "recommended": ["苦瓜", "燕麦", "山药", "葛根"],
        "avoid": ["精制糖", "蜂蜜", "含糖饮料", "精制主食过量"],
        "note": "低 GI 就是吃了血糖升得慢",
        "source_lesson": "第14课 P14",
    },
    "高血脂": {
        "name": "高血脂",
        "principle": "低脂·高膳食纤维",
        "recommended": ["山楂", "黑木耳", "燕麦", "海带", "洋葱"],
        "avoid": ["动物油脂", "油炸食品", "肥肉"],
        "note": "膳食纤维有助于脂质代谢",
        "source_lesson": "第14课 P14",
    },
    "肥胖": {
        "name": "肥胖",
        "principle": "控制能量·增加饱腹感",
        "recommended": ["冬瓜", "薏米", "荷叶", "白萝卜"],
        "avoid": ["高糖高脂", "夜宵", "含糖饮料"],
        "note": "利水消脂的思路",
        "source_lesson": "第14课 P14",
    },
}

# 记录本次扩容
d["_meta"]["decisions"]["P1_rules_expanded"] = "2026-09-23 补入慢性（慢病）饮食指导 4 条（第14课 P14）+ 引擎新增协同增效 good 级提示"
d["_meta"]["version"] = "2.1"

json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("chronic_diet_guidance:", len(d["chronic_diet_guidance"]) - 1, "条")
print("rules version:", d["_meta"]["version"])
