from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Ingredient
from schemas import IngredientDetail

router = APIRouter(prefix='/api/ingredients', tags=['食材'])

@router.get('/', response_model=List[IngredientDetail])
def get_ingredients(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Ingredient)
    if category:
        query = query.filter(Ingredient.category.contains(category))
    return query.all()

@router.get('/{ingredient_id}', response_model=IngredientDetail)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    return db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
