from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ml.feature_schema import InputError, range_warnings

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Prediction, User
from ..schemas import HistoryOut, PredictionOut, PredictRequest
from ..services import prediction_service

router = APIRouter(prefix="/api", tags=["predictions"])


def _out(p: Prediction) -> PredictionOut:
    return PredictionOut(id=p.id, predicted_class=p.predicted_class, predicted_label=p.predicted_label,
                         model_score=p.model_score, model_version=p.model_version, inputs=p.inputs,
                         warnings=range_warnings(p.inputs), created_at=p.created_at)


def _owned(db: Session, user: User, pid: int) -> Prediction:
    p = db.scalar(select(Prediction).where(Prediction.id == pid, Prediction.user_id == user.id))
    if p is None:  # 404 (not 403) so other users' ids are not revealed
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prediction not found")
    return p


@router.post("/predict", response_model=PredictionOut, status_code=status.HTTP_201_CREATED)
def predict(body: PredictRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = prediction_service.predict(body.inputs)
    except InputError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"message": "Please correct the inputs.", "errors": e.errors})
    except prediction_service.ModelUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    p = Prediction(user_id=user.id, predicted_class=result["predicted_class"],
                   predicted_label=result["predicted_label"], inputs=result["inputs"],
                   model_score=result["model_score"], model_version=result["model_version"])
    db.add(p)
    db.commit()
    db.refresh(p)
    return _out(p)


@router.get("/predictions/history", response_model=HistoryOut)
def history(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Prediction).where(Prediction.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Prediction.created_at.desc(), Prediction.id.desc()).offset(skip).limit(limit)).all()
    return HistoryOut(items=[_out(r) for r in rows], total=total, skip=skip, limit=limit)


@router.get("/predictions/{prediction_id}", response_model=PredictionOut)
def get_prediction(prediction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(_owned(db, user, prediction_id))


@router.delete("/predictions/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prediction(prediction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, prediction_id))
    db.commit()
