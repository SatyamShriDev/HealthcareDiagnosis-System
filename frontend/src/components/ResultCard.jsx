import { AlertTriangle, CircleCheck, HeartPulse } from "lucide-react";
import Disclaimer from "./Disclaimer.jsx";

export const fmtDate = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

function displayValue(f, v) {
  if (f.kind === "category") return f.options.find((o) => o.value === v)?.label ?? String(v);
  return `${v}${f.unit && f.unit !== "0-3" ? " " + f.unit : ""}`;
}

export default function ResultCard({ prediction, features }) {
  const high = prediction.predicted_class === 1;
  return (
    <section className="card result" aria-live="polite">
      <div className={"result-head " + (high ? "high" : "low")}>
        {high ? <HeartPulse size={28} aria-hidden /> : <CircleCheck size={28} aria-hidden />}
        <div>
          <p className="eyebrow">Model output (not a diagnosis)</p>
          <h2>{prediction.predicted_label}</h2>
        </div>
      </div>

      {prediction.model_score != null && (
        <p className="score">
          Model score for this class: <strong>{(prediction.model_score * 100).toFixed(1)}%</strong>
          <span className="muted"> — an uncalibrated model output, not the medical probability that you have or do not have a condition.</span>
        </p>
      )}

      {prediction.warnings?.length > 0 && (
        <div className="warn" role="alert">
          <AlertTriangle size={18} aria-hidden />
          <ul>{prediction.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      <h3>About this result</h3>
      <p>
        The model compares your 13 inputs with patterns in a small public heart-disease dataset (about 296 patients) and
        outputs which of its two labels fits better. It does not consider your full medical history, and it cannot confirm or
        rule out any condition. Please discuss any health concern with a qualified healthcare professional.
      </p>

      <h3>Values submitted</h3>
      <dl className="inputs">
        {features.map((f) => (
          <div key={f.name}><dt>{f.label}</dt><dd>{displayValue(f, prediction.inputs[f.name])}</dd></div>
        ))}
      </dl>
      <p className="muted small">Predicted {fmtDate(prediction.created_at)} · model {prediction.model_version}</p>
      <Disclaimer text={prediction.disclaimer} />
    </section>
  );
}
