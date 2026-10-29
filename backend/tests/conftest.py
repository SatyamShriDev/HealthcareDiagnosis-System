"""Test setup.

IMPORTANT: the real heart.csv is not bundled, so these tests build a throw-away model from RANDOM
synthetic rows that follow the real feature schema. This verifies the plumbing (schema -> encoding ->
model -> API -> DB). It says NOTHING about clinical accuracy; real metrics come from ml/train_model.py.
"""
import os
import tempfile
import uuid
from pathlib import Path

import joblib
import numpy as np
import pytest

_tmp = Path(tempfile.mkdtemp())
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["MODEL_PATH"] = str(_tmp / "model.joblib")

from fastapi.testclient import TestClient  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from ml.feature_schema import FEATURES, FEATURE_ORDER, to_frame  # noqa: E402


def sample_inputs(rng) -> dict:
    row = {}
    for f in FEATURES:
        if f["kind"] == "category":
            row[f["name"]] = f["options"][rng.integers(len(f["options"]))]["value"]
        else:
            lo, hi = f["training_range"]
            v = rng.uniform(lo, hi)
            row[f["name"]] = int(round(v)) if f["integer"] else round(float(v), 1)
    return row


@pytest.fixture(scope="session", autouse=True)
def synthetic_model():
    rng = np.random.default_rng(0)
    rows = [sample_inputs(rng) for _ in range(300)]
    X = to_frame(rows)
    y = (X["num_major_vessels"] + X["st_depression"] + rng.normal(0, 1, len(X)) > 1.5).astype(int)
    model = LogisticRegression(max_iter=500).fit(X, y)
    joblib.dump({"model": model, "feature_order": FEATURE_ORDER, "classes": [0, 1], "metrics": {},
                 "model_version": "test-synthetic", "trained_at": "n/a", "dataset_rows": 300}, os.environ["MODEL_PATH"])
    return model


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def valid_inputs():
    return sample_inputs(np.random.default_rng(1))


def make_user(client):
    email = f"{uuid.uuid4().hex[:10]}@example.com"
    pw = "correct-horse-1"
    r = client.post("/api/auth/register", json={"name": "Test User", "email": email, "password": pw})
    assert r.status_code == 201, r.text
    tok = client.post("/api/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    return email, pw, {"Authorization": f"Bearer {tok}"}


@pytest.fixture()
def user(client):
    return make_user(client)
