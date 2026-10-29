from fastapi import APIRouter

from ml.feature_schema import CLASS_LABELS, public_schema

from ..services import prediction_service

router = APIRouter(prefix="/api", tags=["model"])


@router.get("/features")
def features():
    """Input schema derived from the model's feature schema (names, order, options, ranges)."""
    return {"features": public_schema(), "classes": {str(k): v for k, v in CLASS_LABELS.items()}}


@router.get("/model-info")
def model_info():
    """Offline evaluation metrics measured at training time (not per-user results)."""
    return prediction_service.get_model_info()
