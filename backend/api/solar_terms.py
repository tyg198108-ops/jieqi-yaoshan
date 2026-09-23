from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import SolarTerm
from schemas import SolarTermDetail
from datetime import datetime

router = APIRouter(prefix='/api/solar-terms', tags=['节气'])

@router.get('/', response_model=List[SolarTermDetail])
def get_all_solar_terms(db: Session = Depends(get_db)):
    return db.query(SolarTerm).order_by(SolarTerm.order).all()

@router.get('/current', response_model=SolarTermDetail)
def get_current_solar_term(db: Session = Depends(get_db)):
    # 简化版：根据月份判断当前节气区间，实际可以用精确算法
    month = datetime.now().month
    day = datetime.now().day
    
    # 简单映射（精确算法后续可以优化）
    term_order_map = [
        (1, 5, 23), (1, 20, 24), (2, 4, 1), (2, 19, 2),
        (3, 5, 3), (3, 20, 4), (4, 4, 5), (4, 20, 6),
        (5, 5, 7), (5, 21, 8), (6, 5, 9), (6, 21, 10),
        (7, 7, 11), (7, 22, 12), (8, 7, 13), (8, 23, 14),
        (9, 7, 15), (9, 23, 16), (10, 8, 17), (10, 23, 18),
        (11, 7, 19), (11, 22, 20), (12, 7, 21), (12, 22, 22)
    ]
    
    current_order = 1
    for m, d, order in term_order_map:
        if (month > m) or (month == m and day >= d):
            current_order = order
    
    term = db.query(SolarTerm).filter(SolarTerm.order == current_order).first()
    if not term:
        term = db.query(SolarTerm).filter(SolarTerm.order == 1).first()
    return term

@router.get('/{term_id}', response_model=SolarTermDetail)
def get_solar_term(term_id: int, db: Session = Depends(get_db)):
    return db.query(SolarTerm).filter(SolarTerm.id == term_id).first()
