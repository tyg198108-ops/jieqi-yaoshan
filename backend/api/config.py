"""只读配置接口：产品角色矩阵、规则库、人群列表。

这些是「配置型数据」，不进数据库，直接从 data/ 下的 JSON 读，
保证前端与引擎用的是同一份事实源（数据源唯一原则）。
"""
import json
import os
from typing import List, Dict, Any

from fastapi import APIRouter

DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')

router = APIRouter(prefix='/api/config', tags=['配置'])


def _load(filename: str) -> Any:
    with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


@router.get('/profile')
def get_profile():
    """产品角色矩阵与 LLM 策略（product_profile.json）"""
    return _load('product_profile.json')


@router.get('/rules')
def get_rules():
    """完整规则库（rules.json），与后端引擎用的是同一个文件"""
    return _load('rules.json')


@router.get('/groups')
def get_groups() -> List[Dict[str, str]]:
    """特殊人群下拉选项"""
    rules = _load('rules.json')
    groups = rules.get('special_group_contraindications', {})
    out = [{'key': k, 'name': (v or {}).get('name', k)} for k, v in groups.items()]
    out.sort(key=lambda x: (x['key'] != 'none', x['key']))
    return out


@router.get('/chronic')
def get_chronic():
    """慢病饮食指导（来自第14课）"""
    rules = _load('rules.json')
    return rules.get('chronic_diet_guidance', {})
