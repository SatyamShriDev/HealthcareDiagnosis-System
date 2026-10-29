"""Loads the trained artifact once and runs real model predictions."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import joblib

from ml.feature_schema import CLASS_LABELS, FEATURE_ORDER, range_warnings, to_frame, validate_inputs

log = logging.getLogger(__name__)
_lock = threading.Lock()
_cache: dict[str, dict] = {}


class ModelUnavailable(RuntimeError):
    pass


def _default_path() -> str:
    from app.config import settings
    return settings.model_path


def load_artifact(path: str | None = None) -> dict:
    path = path or _default_path()
    with _lock:
        if path in _cache:
            return _cache[path]
        p = Path(path)
        if not p.exists():
            raise ModelUnavailable("Model file not found. Train it first: `python -m ml.train_model`.")
        try:
            art = joblib.load(p)  # trusted, locally trained file only; never load user uploads
        except Exception:  # noqa: BLE001
            log.exception("Failed to load model artifact")
            raise ModelUnavailable("Model file could not be loaded (library version mismatch?). Retrain it.")
        if art.get("feature_order") != FEATURE_ORDER:
            raise ModelUnavailable("Model feature order does not match the current schema. Retrain the model.")
        _cache[path] = art
        return art


def get_model_info(path: str | None = None) -> dict[str, Any]:
    try:
        art = load_artifact(path)
    except ModelUnavailable as e:
        return {"available": False, "reason": str(e)}
    return {"available": True, "model_version": art["model_version"], "trained_at": art["trained_at"],
            "dataset_rows": art["dataset_rows"], "metrics": art["metrics"]}


def predict(inputs: Any, path: str | None = None) -> dict[str, Any]:
    """Validate -> encode with the training schema -> real model.predict / predict_proba."""
    clean = validate_inputs(inputs)  # raises InputError
    art = load_artifact(path)
    model = art["model"]
    X = to_frame([clean])
    try:
        cls = int(model.predict(X)[0])
        score = None
        if hasattr(model, "predict_proba"):
            score = float(model.predict_proba(X)[0][list(model.classes_).index(cls)])
    except Exception:  # noqa: BLE001
        log.exception("Prediction failed")
        raise ModelUnavailable("The model failed to produce a prediction.")
    return {"inputs": clean, "predicted_class": cls, "predicted_label": CLASS_LABELS[cls],
            "model_score": score, "model_version": art["model_version"], "warnings": range_warnings(clean)}