import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { fmtDate } from "../components/ResultCard.jsx";

export default function DashboardPage() {
  const { user } = useAuth();
  const [hist, setHist] = useState(null);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.history(0, 100).then(setHist).catch((e) => setError(e.message));
    api.modelInfo().then(setInfo).catch(() => setInfo(null));
  }, []);

  const items = hist?.items ?? [];
  const chart = [...items].filter((p) => p.model_score != null).reverse()
    .map((p, i) => ({ n: i + 1, score: Math.round(p.model_score * 1000) / 10, label: p.predicted_label }));
  const acc = info?.available ? info.metrics?.cross_validation_5fold?.accuracy?.mean : null;

  return (
    <div className="container page">
      <h1>Welcome, {user.name.split(" ")[0]}</h1>
      {error && <p className="alert alert-error" role="alert">{error}</p>}

      <div className="grid-3">
        <div className="card stat"><p className="muted">Predictions made</p><p className="stat-num">{hist ? hist.total : "…"}</p></div>
        <div className="card stat"><p className="muted">Most recent result</p>
          <p className="stat-text">{items[0] ? items[0].predicted_label : hist ? "None yet" : "…"}</p>
          {items[0] && <p className="muted small">{fmtDate(items[0].created_at)}</p>}</div>
        <div className="card stat"><p className="muted">Model offline accuracy (5-fold CV)</p>
          <p className="stat-num">{acc != null ? `${(acc * 100).toFixed(1)}%` : "n/a"}</p>
          <p className="muted small">{acc != null ? "Measured at training time on a small dataset; not clinical validation." : "Model not trained yet."}</p></div>
      </div>

      <div className="row-between">
        <h2>Recent activity</h2>
        <Link className="btn btn-primary" to="/predict">New prediction</Link>
      </div>

      {hist && items.length === 0 && (
        <div className="card empty"><p>You have no predictions yet.</p><Link className="btn btn-outline" to="/predict">Make your first prediction</Link></div>
      )}

      {items.length > 0 && (
        <>
          <div className="card">
            {items.slice(0, 5).map((p) => (
              <Link key={p.id} to={`/predictions/${p.id}`} className="list-row">
                <span><strong>{p.predicted_label}</strong><br /><span className="muted small">{fmtDate(p.created_at)}</span></span>
                <span>{p.model_score != null ? `${(p.model_score * 100).toFixed(1)}%` : "—"}</span>
              </Link>
            ))}
            <Link to="/history" className="muted small">View all history →</Link>
          </div>
          {chart.length >= 2 && (
            <div className="card">
              <h3>Model score per prediction</h3>
              <div style={{ width: "100%", height: 240 }}>
                <ResponsiveContainer>
                  <LineChart data={chart} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="n" label={{ value: "Prediction #", position: "insideBottom", offset: -2 }} />
                    <YAxis domain={[0, 100]} unit="%" />
                    <Tooltip formatter={(v, _n, p) => [`${v}%`, p.payload.label]} />
                    <Line type="monotone" dataKey="score" stroke="var(--primary)" strokeWidth={2} dot />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="muted small">Score of the predicted class (uncalibrated), oldest to newest.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
