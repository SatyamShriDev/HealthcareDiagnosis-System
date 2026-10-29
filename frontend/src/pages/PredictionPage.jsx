import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import Disclaimer from "../components/Disclaimer.jsx";
import ResultCard from "../components/ResultCard.jsx";

export default function PredictionPage() {
  const [features, setFeatures] = useState(null);
  const [values, setValues] = useState({});
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => { api.features().then((d) => setFeatures(d.features)).catch((e) => setError(e.message)); }, []);

  function validate() {
    const e = {};
    for (const f of features) {
      const v = values[f.name];
      if (v === undefined || v === "") { e[f.name] = "This field is required."; continue; }
      if (f.kind === "number") {
        const n = Number(v);
        if (!Number.isFinite(n)) e[f.name] = "Enter a number.";
        else if (n < f.min || n > f.max) e[f.name] = `Must be between ${f.min} and ${f.max}.`;
        else if (f.integer && !Number.isInteger(n)) e[f.name] = "Enter a whole number.";
      }
    }
    return e;
  }

  async function onSubmit(ev) {
    ev.preventDefault();
    if (busy) return;
    setError("");
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) { setError("Please fix the highlighted fields."); return; }
    const payload = {};
    features.forEach((f) => { payload[f.name] = f.kind === "number" ? Number(values[f.name]) : values[f.name]; });
    setBusy(true);
    try {
      setResult(await api.predict(payload));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      if (err.fieldErrors) setErrors(err.fieldErrors);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const reset = () => { setResult(null); setValues({}); setErrors({}); setError(""); };

  if (!features) return <div className="container page">{error ? <p className="alert alert-error" role="alert">{error}</p> : <span className="spinner" aria-label="Loading form" />}</div>;

  if (result) {
    return (
      <div className="container page narrow">
        <ResultCard prediction={result} features={features} />
        <div className="row">
          <button className="btn btn-primary" onClick={reset}>Start another prediction</button>
          <Link className="btn btn-outline" to="/history">View history</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container page narrow">
      <h1>New prediction</h1>
      <p className="muted">Enter the 13 clinical values the model was trained on. Nothing is pre-filled or assumed. Leave out a value and the form will not submit.</p>
      <Disclaimer />
      <form className="card form-grid" onSubmit={onSubmit} noValidate>
        {error && <p className="alert alert-error full" role="alert">{error}</p>}
        {features.map((f) => (
          <div className="field" key={f.name}>
            <label htmlFor={f.name}>{f.label}{f.unit && f.kind === "number" && f.unit !== "0-3" ? ` (${f.unit})` : ""}</label>
            {f.kind === "category" ? (
              <select id={f.name} value={values[f.name] ?? ""} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} aria-invalid={!!errors[f.name]}>
                <option value="" disabled>Select…</option>
                {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : (
              <input id={f.name} type="number" inputMode="decimal" min={f.min} max={f.max} step={f.step} value={values[f.name] ?? ""}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} aria-invalid={!!errors[f.name]} />
            )}
            <span className="muted small">{f.help}{f.kind === "number" ? ` Training data range: ${f.training_range[0]}–${f.training_range[1]}.` : ""}</span>
            {errors[f.name] && <span className="field-error">{errors[f.name]}</span>}
          </div>
        ))}
        <div className="full row">
          <button className="btn btn-primary btn-lg" disabled={busy}>{busy ? "Predicting…" : "Get prediction"}</button>
          <button type="button" className="btn btn-ghost" onClick={reset} disabled={busy}>Clear all</button>
        </div>
      </form>
    </div>
  );
}
