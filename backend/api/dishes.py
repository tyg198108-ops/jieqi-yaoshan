from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Dish
from schemas import DishDetail

router = APIRouter(prefix='/api/dishes', tags=['菜品'])

@router.get('/', response_model=List[DishDetail])
def get_dishes(dish_type: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Dish)
    if dish_type:
        query = query.filter(Dish.dish_type == dish_type)
    if category:
        query = query.filter(Dish.category.contains(category))
    return query.all()

@router.get('/{dish_id}', response_model=DishDetail)
def get_dish(dish_id: int, db: Session = Depends(get_db)):
    return db.query(Dish).filter(Dish.id == dish_id).first()
