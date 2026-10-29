# HeartWise – Heart-Risk Prediction (educational demo)

Full-stack student project: **React (Vite) + FastAPI + SQLite + scikit-learn/LightGBM**.
Users register, log in, enter 13 clinical measurements, get a real-model prediction, and review private history.

> **Educational demonstration only.** Not a medical device, not clinically validated, not a diagnosis.
> Emergency symptoms need urgent medical care, not this website.

## Read this first: what the supplied notebook actually is

The notebook `heart-disease-predictions.ipynb` uses the **Cleveland heart-disease dataset**
(`heart.csv`, 303 rows × 14 columns, binary `target`). It is **not** a symptom → disease dataset, so there is
no symptom checklist and no multi-disease output. The app therefore:

- shows a **form generated from the model's 13 real input features** (`GET /api/features`), and
- predicts one of two classes from the notebook: `1` = heart disease, `0` = no disease.

Other gaps you must be aware of:

| Item | Status |
|---|---|
| `heart.csv` | **Not supplied and not bundled.** Download the Kaggle "heart-disease" `heart.csv` and put it at `backend/data/heart.csv`. |
| Trained model | Notebook never saved one. `backend/ml/train_model.py` reproduces it (tuned LightGBM, notebook cells 9–12, 42–43, 65–66). |
| YouTube reference video | **Could not be accessed** (fetch was blocked). The UI is *not* modelled on the video; it uses the default teal healthcare style from the spec. |
| Evaluation metrics | **None measured yet.** The notebook reported ~86% accuracy on a 74-row hold-out (its own, non-stratified split). `train_model.py` prints and saves *its* numbers (stratified hold-out + 5-fold CV) when you run it. Don't quote numbers until you have. |

Label caveat: the notebook treats `target = 1` as disease. Several sources note the Kaggle copy's label meaning
may be inverted relative to the original UCI data (the notebook's own EDA finds lower ST depression and more
vessels associated with *no* disease, which is clinically odd). The app follows the notebook, but this is another
reason not to treat output as meaningful medically.

## Model & preprocessing (from the notebook)

1. Drop rows with `ca >= 4` or `thal == 0` (303 → 296).
2. Rename columns and decode categories to strings (e.g. `cp` → `chest_pain_type`).
3. Label-encode categoricals (sorted-alphabetical codes, same as `sklearn.LabelEncoder`; implemented once in
   `ml/feature_schema.py` and used by both training and serving, so feature order/encoding can't drift).
4. `LGBMClassifier(max_depth=5, min_data_in_leaf=80, num_leaves=20)`.

Deliberate differences: stratified split (`test_size=0.25`, `random_state=0`) and extra 5-fold CV.
The deployed model is the one evaluated on the hold-out (trained on the train split only).

`model_score` in API/UI is `predict_proba` of the predicted class. It is **uncalibrated** and labelled as such.
Inputs outside the training ranges produce a visible warning.

## Structure

```
backend/
  app/            main.py, config.py, database.py, models.py, schemas.py, security.py, dependencies.py
    routers/      auth.py, features.py, predictions.py
    services/     prediction_service.py   (loads model once, validates, predicts)
  ml/             feature_schema.py (single source of truth), train_model.py, artifacts/
  data/           put heart.csv here
  tests/          pytest suite
frontend/src/     api/client.js, context/AuthContext.jsx, components/, pages/, styles/global.css
```

## Setup (macOS / Linux / Windows)

Prerequisites: Python 3.10–3.12, Node.js 18+.

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET in .env
# place heart.csv in backend/data/, then train:
python -m ml.train_model --data data/heart.csv
uvicorn app.main:app --reload --port 8000
```
Tables are created automatically at startup (`Base.metadata.create_all`); the SQLite file is `backend/app.db`.
Alembic is not used (not needed for a single-schema student project). To use PostgreSQL later, set `DATABASE_URL`
and install a driver such as `psycopg`.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_URL=http://localhost:8000
npm run dev              # http://localhost:5173
```

Without a trained model the site still runs; `/api/predict` returns `503` with instructions.

## Environment variables (`backend/.env`)

| Name | Purpose |
|---|---|
| `JWT_SECRET` | **Required**, ≥32 random chars |
| `ACCESS_TOKEN_MINUTES` | Token lifetime (default 60) |
| `DATABASE_URL` | Default SQLite file |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `MODEL_PATH` | Default `ml/artifacts/heart_model.joblib` |

## API

| Method & path | Auth | Notes |
|---|---|---|
| `GET /health`, `/api/health` | – | status + `model_loaded` |
| `POST /api/auth/register` | – | `{name,email,password≥8}` → 201 user; 409 duplicate |
| `POST /api/auth/login` | – | `{email,password}` → `{access_token,token_type,user}`; 401 on bad credentials |
| `GET /api/auth/me` | ✔ | current user |
| `GET /api/features` | – | model input schema (names, order, options, ranges). *Replaces the spec's `/api/symptoms`.* |
| `GET /api/model-info` | – | offline metrics from training (if model exists) |
| `POST /api/predict` | ✔ | `{inputs:{<13 features>}}` → 201 prediction; 422 `{detail:{message,errors}}`; 503 if no model |
| `GET /api/predictions/history?skip&limit` | ✔ | only the caller's records |
| `GET /api/predictions/{id}` | ✔ | 404 if not yours |
| `DELETE /api/predictions/{id}` | ✔ | 204; 404 if not yours |

Identity always comes from the JWT; the client never sends a `user_id`.

## Tests

```bash
cd backend && pytest
```
Covers: health, register/duplicate/login/invalid credentials, auth on protected routes, schema endpoint,
empty/unknown/out-of-range/malformed inputs, a prediction compared against an **independent** call to the model,
history persistence, empty history, cross-user isolation (404), encoding order.
**The test model is built from random synthetic rows that follow the real schema** (the real dataset isn't bundled),
so tests verify plumbing only, not accuracy.

Manual end-to-end checklist: register → log out → log in → open `/dashboard` (empty state) → New prediction with an
empty form (blocked) → fill all fields → result + disclaimer → History shows it → delete it → open a protected URL
while logged out (redirected to login) → stop the backend and submit (friendly network error).

## Security notes / limitations

- bcrypt password hashes; signed JWTs; secrets only via env; CORS limited to configured origins; ownership checks on every record.
- The JWT lives in `sessionStorage` (readable by any XSS). Acceptable for a local demo; production should use
  HttpOnly cookies + CSRF protection, HTTPS, rate limiting/lockout, secret management, and refresh-token handling.
- Model files are loaded only from the configured local path (joblib/pickle must never be loaded from untrusted sources).
- Small dataset (296 rows), no calibration, no external validation, no explanations beyond neutral text. No disease
  descriptions or treatment content are included because no vetted content source was supplied.

## Verification status (honest)

Run in the authoring sandbox (no internet): Python compile check of all backend files; the schema, encoding, input
validation and prediction-service logic exercised with a scikit-learn stand-in model; `train_model.load_clean`
checked on a synthetic raw-format CSV.
**Not run** (packages unavailable offline): `pytest`, the FastAPI server, LightGBM training, `npm install`, `npm run build`,
and any browser testing. Expect to fix small issues on first run and tell me the error output.
