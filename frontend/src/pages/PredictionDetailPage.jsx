import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import ResultCard from "../components/ResultCard.jsx";

export default function PredictionDetailPage() {
  const { id } = useParams();
  const [pred, setPred] = useState(null);
  const [features, setFeatures] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.prediction(id), api.features()])
      .then(([p, f]) => { setPred(p); setFeatures(f.features); })
      .catch((e) => setError(e.status === 404 ? "Prediction not found." : e.message));
  }, [id]);

  return (
    <div className="container page narrow">
      <Link to="/history" className="muted">← Back to history</Link>
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      {!error && !pred && <span className="spinner" aria-label="Loading" />}
      {pred && features && <ResultCard prediction={pred} features={features} />}
    </div>
  );
}
