"""Reproduce the notebook's final model (tuned LightGBM) and save a joblib artifact.

Usage (from backend/):  python -m ml.train_model --data data/heart.csv

Follows heart-disease-predictions.ipynb:
  * drop rows with ca >= 4 or thal == 0   (cell 9)       -> 296 rows
  * rename columns + decode categories    (cells 11-12)
  * LabelEncoder-style codes              (cell 42; see feature_schema.encode_value)
  * LGBMClassifier(max_depth=5, min_data_in_leaf=80, num_leaves=20)  (cells 65-66)
Differences from the notebook (deliberate): the hold-out split is STRATIFIED, and we also report
5-fold stratified cross-validation, because a single 74-row hold-out is a very noisy estimate.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from lightgbm import LGBMClassifier

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

from ml.feature_schema import FEATURE_ORDER, to_frame


RENAME = {"cp": "chest_pain_type", "trestbps": "resting_blood_pressure", "chol": "cholesterol",
          "fbs": "fasting_blood_sugar", "restecg": "resting_electrocardiogram",
          "thalach": "max_heart_rate_achieved", "exang": "exercise_induced_angina", "oldpeak": "st_depression",
          "slope": "st_slope", "ca": "num_major_vessels", "thal": "thalassemia"}
CODE_MAPS = {  # notebook cell 12
    "sex": {0: "female", 1: "male"},
    "chest_pain_type": {0: "typical angina", 1: "atypical angina", 2: "non-anginal pain", 3: "asymptomatic"},
    "fasting_blood_sugar": {0: "lower than 120mg/ml", 1: "greater than 120mg/ml"},
    "resting_electrocardiogram": {0: "normal", 1: "ST-T wave abnormality", 2: "left ventricular hypertrophy"},
    "exercise_induced_angina": {0: "no", 1: "yes"},
    "st_slope": {0: "upsloping", 1: "flat", 2: "downsloping"},
    "thalassemia": {1: "fixed defect", 2: "normal", 3: "reversable defect"},
}
LGBM_PARAMS = dict(max_depth=5, min_data_in_leaf=80, num_leaves=20)  # notebook cell 65 best params
REQUIRED_COLUMNS = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal", "target",
]

RENAME = {
    "sex": "sex",
    "cp": "chest_pain_type",
    "trestbps": "resting_blood_pressure",
    "chol": "cholesterol",
    "fbs": "fasting_blood_sugar",
    "restecg": "resting_electrocardiogram",
    "thalach": "max_heart_rate_achieved",
    "exang": "exercise_induced_angina",
    "oldpeak": "st_depression",
    "slope": "st_slope",
    "ca": "num_major_vessels",
    "thal": "thalassemia",
}

LGBM_PARAMS = dict(max_depth=5, min_data_in_leaf=80, num_leaves=20)


def load_clean(csv_path: Path) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(csv_path)

    # Keep Cleveland records when the dataset contains multiple hospitals.
    if "dataset" in df.columns:
        df = df[
            df["dataset"].astype(str).str.casefold() == "cleveland"
        ].copy()

    # Support the original UCI dataset's column names.
    source_renames = {}

    if "thalch" in df.columns and "thalach" not in df.columns:
        source_renames["thalch"] = "thalach"

    if "num" in df.columns and "target" not in df.columns:
        source_renames["num"] = "target"

    df = df.rename(columns=source_renames)

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Unexpected columns in {csv_path}. "
            f"Missing required columns: {missing}. "
            f"Found: {list(df.columns)}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    # Remove rows with missing required values.
    df = df.dropna(subset=REQUIRED_COLUMNS)

    df["ca"] = pd.to_numeric(df["ca"], errors="coerce")
    df["target"] = pd.to_numeric(df["target"], errors="coerce")

    df = df.dropna(subset=["ca", "target"])

    # Remove invalid major-vessel values.
    df = df[df["ca"] < 4].copy()

    # Target 0 = no heart disease; targets 1–4 = heart disease.
    df["target"] = (df["target"] > 0).astype(int)

    df = df.rename(columns=RENAME)

    # Convert dataset categories into the values expected by the API.
    category_maps = {
        "sex": {
            "female": "female",
            "male": "male",
        },
        "chest_pain_type": {
            "typical angina": "typical angina",
            "atypical angina": "atypical angina",
            "non-anginal": "non-anginal pain",
            "non-anginal pain": "non-anginal pain",
            "asymptomatic": "asymptomatic",
        },
        "fasting_blood_sugar": {
            "false": "lower than 120mg/ml",
            "true": "greater than 120mg/ml",
            "0": "lower than 120mg/ml",
            "1": "greater than 120mg/ml",
        },
        "resting_electrocardiogram": {
            "normal": "normal",
            "st-t abnormality": "ST-T wave abnormality",
            "lv hypertrophy": "left ventricular hypertrophy",
        },
        "exercise_induced_angina": {
            "false": "no",
            "true": "yes",
            "0": "no",
            "1": "yes",
            "no": "no",
            "yes": "yes",
        },
        "st_slope": {
            "upsloping": "upsloping",
            "flat": "flat",
            "downsloping": "downsloping",
        },
        "thalassemia": {
            "fixed defect": "fixed defect",
            "normal": "normal",
            "reversable defect": "reversable defect",
        },
    }

    for column, mapping in category_maps.items():
        values = (
            df[column]
            .astype(str)
            .str.strip()
            .str.casefold()
        )

        df[column] = values.map(mapping)

        if df[column].isna().any():
            unknown = sorted(
                values[df[column].isna()].unique().tolist()
            )
            raise ValueError(
                f"Unknown category values in {column}: {unknown}"
            )

    X = to_frame(df[FEATURE_ORDER].to_dict("records"))
    y = df["target"].astype(int)

    return X, y

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the heart disease prediction model."
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to the heart dataset CSV",
    )
    args = parser.parse_args()

    print(f"Reading dataset: {args.data}", flush=True)

    X, y = load_clean(args.data)

    if y.nunique() != 2:
        raise ValueError(
            f"Expected a binary target, found classes: {sorted(y.unique().tolist())}"
        )

    if y.value_counts().min() < 5:
        raise ValueError(
            "Each target class needs at least 5 rows for stratified 5-fold cross-validation."
        )

    print(f"Loaded {len(X)} rows with {len(FEATURE_ORDER)} features.")
    print("Target counts:", y.value_counts().sort_index().to_dict())

    # Split the dataset into training and testing sets.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    # Initialize the LightGBM model.
    model = LGBMClassifier(
        **LGBM_PARAMS,
        n_estimators=100,
        learning_rate=0.05,
        random_state=42,
        verbosity=-1,
    )

    # Perform 5-fold cross-validation.
    print("\nRunning 5-fold cross-validation...", flush=True)

    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    cv_scores = cross_validate(
        model,
        X_train,
        y_train,
        cv=cv,
        scoring={
            "accuracy": "accuracy",
            "f1": "f1",
            "roc_auc": "roc_auc",
        },
        error_score="raise",
    )

    print(
        "Cross-validation accuracy:",
        round(float(np.mean(cv_scores["test_accuracy"])), 4),
    )
    print(
        "Cross-validation F1:",
        round(float(np.mean(cv_scores["test_f1"])), 4),
    )
    print(
        "Cross-validation ROC-AUC:",
        round(float(np.mean(cv_scores["test_roc_auc"])), 4),
    )

    # Train the final model.
    print("\nTraining final model...", flush=True)

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    # Calculate evaluation metrics.
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(
            precision_score(y_test, predictions, zero_division=0)
        ),
        "recall": float(
            recall_score(y_test, predictions, zero_division=0)
        ),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(
            y_test, predictions
        ).tolist(),
        "cv_accuracy_mean": float(
            np.mean(cv_scores["test_accuracy"])
        ),
        "cv_f1_mean": float(np.mean(cv_scores["test_f1"])),
        "cv_roc_auc_mean": float(
            np.mean(cv_scores["test_roc_auc"])
        ),
    }

    # Create the artifacts directory.
    artifact_dir = Path("ml/artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_dir / "heart_model.joblib"
    metrics_path = artifact_dir / "metrics.json"

    trained_at = datetime.now(timezone.utc).isoformat()

    # Save the model and its metadata.
    artifact = {
        "model": model,
        "feature_order": FEATURE_ORDER,
        "model_version": "1.0.0",
        "trained_at": trained_at,
        "dataset_rows": int(len(X)),
        "metrics": metrics,
    }

    joblib.dump(artifact, artifact_path)

    metrics_path.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print("\nHold-out evaluation metrics:")
    print(json.dumps(metrics, indent=2))

    print(f"\nModel saved to: {artifact_path}")
    print(f"Metrics saved to: {metrics_path}")


if __name__ == "__main__":
    main()