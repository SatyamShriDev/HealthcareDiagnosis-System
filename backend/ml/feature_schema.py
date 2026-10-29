"""Single source of truth for the model's input schema.

Column names, category strings and column ORDER come from the supplied notebook
(heart-disease-predictions.ipynb, cells 11-12, 16 and 43). The notebook label-encodes every
categorical column with sklearn's LabelEncoder, which assigns integer codes in sorted (alphabetical)
order of the string labels. `encode_value` reproduces exactly that, and is used by BOTH training and
prediction so the two can never drift apart.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _opts(*pairs):
    return [{"value": v, "label": l} for v, l in pairs]


# Order == notebook's `data.columns[:-1]` after renaming.
FEATURES: list[dict[str, Any]] = [
    {"name": "age", "label": "Age", "kind": "number", "unit": "years", "min": 1, "max": 120, "step": 1,
     "integer": True, "training_range": [29, 77], "help": "Age in years."},
    {"name": "sex", "label": "Sex", "kind": "category",
     "options": _opts(("female", "Female"), ("male", "Male")), "help": "Sex as recorded in the dataset."},
    {"name": "chest_pain_type", "label": "Chest pain type", "kind": "category",
     "options": _opts(("typical angina", "Typical angina"), ("atypical angina", "Atypical angina"),
                      ("non-anginal pain", "Non-anginal pain"), ("asymptomatic", "Asymptomatic")),
     "help": "Chest pain category used in the dataset."},
    {"name": "resting_blood_pressure", "label": "Resting blood pressure", "kind": "number", "unit": "mm Hg",
     "min": 50, "max": 260, "step": 1, "integer": True, "training_range": [94, 200],
     "help": "Resting blood pressure on admission."},
    {"name": "cholesterol", "label": "Serum cholesterol", "kind": "number", "unit": "mg/dl",
     "min": 80, "max": 700, "step": 1, "integer": True, "training_range": [126, 564],
     "help": "Serum cholesterol."},
    {"name": "fasting_blood_sugar", "label": "Fasting blood sugar above 120 mg/dl", "kind": "category",
     "options": _opts(("lower than 120mg/ml", "No (120 mg/dl or lower)"),
                      ("greater than 120mg/ml", "Yes (above 120 mg/dl)")),
     "help": "Whether fasting blood sugar was above 120 mg/dl."},
    {"name": "resting_electrocardiogram", "label": "Resting ECG result", "kind": "category",
     "options": _opts(("normal", "Normal"), ("ST-T wave abnormality", "ST-T wave abnormality"),
                      ("left ventricular hypertrophy", "Left ventricular hypertrophy")),
     "help": "Resting electrocardiographic result."},
    {"name": "max_heart_rate_achieved", "label": "Maximum heart rate achieved", "kind": "number", "unit": "bpm",
     "min": 40, "max": 250, "step": 1, "integer": True, "training_range": [71, 202],
     "help": "Maximum heart rate reached during the exercise test."},
    {"name": "exercise_induced_angina", "label": "Exercise-induced angina", "kind": "category",
     "options": _opts(("no", "No"), ("yes", "Yes")), "help": "Chest pain induced by exercise."},
    {"name": "st_depression", "label": "ST depression (exercise vs rest)", "kind": "number", "unit": "mm",
     "min": 0, "max": 10, "step": 0.1, "integer": False, "training_range": [0.0, 6.2],
     "help": "ST depression induced by exercise relative to rest."},
    {"name": "st_slope", "label": "Slope of peak exercise ST segment", "kind": "category",
     "options": _opts(("upsloping", "Upsloping"), ("flat", "Flat"), ("downsloping", "Downsloping")),
     "help": "Slope of the peak exercise ST segment."},
    {"name": "num_major_vessels", "label": "Major vessels coloured by fluoroscopy", "kind": "number",
     "unit": "0-3", "min": 0, "max": 3, "step": 1, "integer": True, "training_range": [0, 3],
     "help": "Number of major vessels (0-3) coloured by fluoroscopy."},
    {"name": "thalassemia", "label": "Thalassemia (thal) result", "kind": "category",
     "options": _opts(("fixed defect", "Fixed defect"), ("normal", "Normal"),
                      ("reversable defect", "Reversable defect")),
     "help": "Thallium stress test result category."},
]

FEATURE_ORDER: list[str] = [f["name"] for f in FEATURES]
_BY_NAME = {f["name"]: f for f in FEATURES}

# Notebook target: 1 = disease, 0 = no disease (notebook cell 7 data dictionary).
CLASS_LABELS = {0: "Lower likelihood of heart disease", 1: "Higher likelihood of heart disease"}


class InputError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Invalid inputs")
        self.errors = errors


def encode_value(name: str, value: Any) -> float:
    """Numeric features pass through; categorical ones get LabelEncoder-equivalent codes."""
    f = _BY_NAME[name]
    if f["kind"] == "number":
        return float(value)
    return float(sorted(o["value"] for o in f["options"]).index(value))


def encode_row(row: dict[str, Any]) -> list[float]:
    return [encode_value(n, row[n]) for n in FEATURE_ORDER]


def to_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([encode_row(r) for r in rows], columns=FEATURE_ORDER)


def validate_inputs(raw: Any) -> dict[str, Any]:
    """Strict validation against the schema. Raises InputError with per-field messages."""
    if not isinstance(raw, dict) or not raw:
        raise InputError({"inputs": "No inputs were provided."})
    errors: dict[str, str] = {}
    for key in raw:
        if key not in _BY_NAME:
            errors[str(key)] = "Unknown field."
    clean: dict[str, Any] = {}
    for f in FEATURES:
        n = f["name"]
        if n not in raw or raw[n] is None or raw[n] == "":
            errors[n] = "This field is required."
            continue
        v = raw[n]
        if f["kind"] == "category":
            if v not in [o["value"] for o in f["options"]]:
                errors[n] = "Not a valid option."
            else:
                clean[n] = v
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            errors[n] = "Must be a number."
        elif not (f["min"] <= v <= f["max"]):
            errors[n] = f"Must be between {f['min']} and {f['max']}."
        elif f["integer"] and float(v) != int(v):
            errors[n] = "Must be a whole number."
        else:
            clean[n] = int(v) if f["integer"] else float(v)
    if errors:
        raise InputError(errors)
    return clean


def range_warnings(clean: dict[str, Any]) -> list[str]:
    """Flag values outside the range seen in the training data (model extrapolates there)."""
    out = []
    for f in FEATURES:
        if f["kind"] == "number" and f["name"] in clean:
            lo, hi = f["training_range"]
            if not (lo <= clean[f["name"]] <= hi):
                out.append(f"{f['label']} ({clean[f['name']]}) is outside the range seen in the training data "
                           f"({lo}-{hi}); the model may be unreliable for this value.")
    return out


def public_schema() -> list[dict[str, Any]]:
    return FEATURES
