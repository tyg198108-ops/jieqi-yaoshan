from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import BanquetGenerateRequest, BanquetResponse
from engine.generator import BanquetGenerator

router = APIRouter(prefix='/api/banquet', tags=['宴席生成'])

@router.post('/generate', response_model=BanquetResponse)
def generate_banquet(request: BanquetGenerateRequest, db: Session = Depends(get_db)):
    generator = BanquetGenerator(db)
    return generator.generate(
        solar_term_id=request.solar_term_id,
        main_constitution_id=request.main_constitution_id,
        secondary_constitution_id=request.secondary_constitution_id,
        special_group=request.special_group,
        banquet_type=request.banquet_type,
        flavor_preference=request.flavor_preference,
        banquet_scale=request.banquet_scale,
        headcount=request.headcount,
        finale=request.finale or 'dessert'
    )
