import copy

from app.services import prediction_service
from ml.feature_schema import FEATURE_ORDER, encode_row, to_frame
from tests.conftest import make_user


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_register_duplicate_and_login(client, user):
    email, pw, _ = user
    dup = client.post("/api/auth/register", json={"name": "X", "email": email.upper(), "password": pw})
    assert dup.status_code == 409
    assert client.post("/api/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@example.com", "password": pw}).status_code == 401
    ok = client.post("/api/auth/login", json={"email": email, "password": pw}).json()
    assert ok["token_type"] == "bearer" and "password" not in str(ok) and "password_hash" not in str(ok)


def test_register_validation(client):
    r = client.post("/api/auth/register", json={"name": "A", "email": "not-an-email", "password": "short"})
    assert r.status_code == 422


def test_me_and_protected_endpoints_require_auth(client, user):
    _, _, h = user
    assert client.get("/api/auth/me", headers=h).status_code == 200
    for method, path in [("get", "/api/auth/me"), ("post", "/api/predict"), ("get", "/api/predictions/history"),
                         ("get", "/api/predictions/1"), ("delete", "/api/predictions/1")]:
        assert getattr(client, method)(path).status_code == 401, path
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_features_match_model_schema(client):
    feats = client.get("/api/features").json()["features"]
    assert [f["name"] for f in feats] == FEATURE_ORDER


def test_predict_rejects_bad_input(client, user, valid_inputs):
    _, _, h = user
    assert client.post("/api/predict", json={"inputs": {}}, headers=h).status_code == 422
    unknown = {**valid_inputs, "fever": 1}
    assert client.post("/api/predict", json={"inputs": unknown}, headers=h).status_code == 422
    missing = copy.deepcopy(valid_inputs); missing.pop("age")
    r = client.post("/api/predict", json={"inputs": missing}, headers=h)
    assert r.status_code == 422 and "age" in r.json()["detail"]["errors"]
    for bad in ({"age": 500}, {"sex": "other"}, {"cholesterol": "abc"}, {"num_major_vessels": 1.5}):
        r = client.post("/api/predict", json={"inputs": {**valid_inputs, **bad}}, headers=h)
        assert r.status_code == 422, bad


def test_predict_uses_real_model_and_is_saved(client, user, valid_inputs, synthetic_model):
    _, _, h = user
    r = client.post("/api/predict", json={"inputs": valid_inputs}, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    # Independent recomputation straight from the model object (not a hardcoded expectation).
    X = to_frame([valid_inputs])
    assert list(X.columns) == FEATURE_ORDER
    expected_cls = int(synthetic_model.predict(X)[0])
    expected_p = float(synthetic_model.predict_proba(X)[0][expected_cls])
    assert body["predicted_class"] == expected_cls
    assert abs(body["model_score"] - expected_p) < 1e-9
    assert body["inputs"] == valid_inputs and "disclaimer" in body
    hist = client.get("/api/predictions/history", headers=h).json()
    assert hist["total"] == 1 and hist["items"][0]["id"] == body["id"]


def test_history_empty_for_new_user(client, user):
    _, _, h = user
    assert client.get("/api/predictions/history", headers=h).json() == {"items": [], "total": 0, "skip": 0, "limit": 10}


def test_users_cannot_access_each_others_predictions(client, valid_inputs):
    _, _, h1 = make_user(client)
    _, _, h2 = make_user(client)
    pid = client.post("/api/predict", json={"inputs": valid_inputs}, headers=h1).json()["id"]
    assert client.get(f"/api/predictions/{pid}", headers=h1).status_code == 200
    assert client.get(f"/api/predictions/{pid}", headers=h2).status_code == 404
    assert client.delete(f"/api/predictions/{pid}", headers=h2).status_code == 404
    assert client.get("/api/predictions/history", headers=h2).json()["total"] == 0
    assert client.delete(f"/api/predictions/{pid}", headers=h1).status_code == 204


def test_encoding_is_labelencoder_equivalent(valid_inputs):
    # sorted() order for chest_pain_type: asymptomatic, atypical angina, non-anginal pain, typical angina
    row = {**valid_inputs, "chest_pain_type": "typical angina"}
    assert encode_row(row)[FEATURE_ORDER.index("chest_pain_type")] == 3.0
    row = {**valid_inputs, "resting_electrocardiogram": "ST-T wave abnormality"}
    assert encode_row(row)[FEATURE_ORDER.index("resting_electrocardiogram")] == 0.0  # uppercase sorts first


def test_missing_model_gives_503(tmp_path):
    import pytest
    with pytest.raises(prediction_service.ModelUnavailable):
        prediction_service.load_artifact(str(tmp_path / "nope.joblib"))
