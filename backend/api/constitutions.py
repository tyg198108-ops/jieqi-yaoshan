from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Constitution, ConstitutionQuestion
from schemas import ConstitutionDetail
from pydantic import BaseModel

router = APIRouter(prefix='/api/constitutions', tags=['体质'])

class TestAnswer(BaseModel):
    question_id: int
    score: int

class TestResult(BaseModel):
    main_constitution: ConstitutionDetail
    secondary_constitution: ConstitutionDetail = None
    scores: dict

@router.get('/', response_model=List[ConstitutionDetail])
def get_all_constitutions(db: Session = Depends(get_db)):
    return db.query(Constitution).all()

@router.get('/questions')
def get_constitution_questions(db: Session = Depends(get_db)):
    questions = db.query(ConstitutionQuestion).all()
    return [{'id': q.id, 'constitution_id': q.constitution_id, 'question_text': q.question_text, 'options': q.options} for q in questions]

@router.get('/{constitution_id}', response_model=ConstitutionDetail)
def get_constitution(constitution_id: int, db: Session = Depends(get_db)):
    return db.query(Constitution).filter(Constitution.id == constitution_id).first()

@router.post('/test', response_model=TestResult)
def submit_test(answers: List[TestAnswer], db: Session = Depends(get_db)):
    # 计算每种体质得分
    scores = {}
    constitutions = db.query(Constitution).all()
    for c in constitutions:
        scores[c.id] = 0
    
    for ans in answers:
        q = db.query(ConstitutionQuestion).filter(ConstitutionQuestion.id == ans.question_id).first()
        if q:
            scores[q.constitution_id] += ans.score
    
    # 找出得分最高的两种体质
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    main_id = sorted_scores[0][0]
    secondary_id = sorted_scores[1][0] if len(sorted_scores) > 1 and sorted_scores[1][1] >= sorted_scores[0][1] * 0.5 else None
    
    main_const = db.query(Constitution).filter(Constitution.id == main_id).first()
    secondary_const = db.query(Constitution).filter(Constitution.id == secondary_id).first() if secondary_id else None
    
    return TestResult(
        main_constitution=main_const,
        secondary_constitution=secondary_const,
        scores={str(k): v for k, v in scores}
    )
