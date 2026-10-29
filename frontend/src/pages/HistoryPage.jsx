import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trash2 } from "lucide-react";
import { api } from "../api/client.js";
import { fmtDate } from "../components/ResultCard.jsx";

const PAGE = 10;

export default function HistoryPage() {
  const [skip, setSkip] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    api.history(skip, PAGE).then((d) => {
      if (d.items.length === 0 && skip > 0) setSkip(Math.max(0, skip - PAGE)); else setData(d);
    }).catch((e) => setError(e.message));
  }, [skip]);
  useEffect(load, [load]);

  async function remove(id) {
    if (!window.confirm("Delete this prediction from your history?")) return;
    try { await api.deletePrediction(id); load(); } catch (e) { setError(e.message); }
  }

  return (
    <div className="container page">
      <div className="row-between"><h1>Prediction history</h1><Link className="btn btn-primary" to="/predict">New prediction</Link></div>
      {error && <p className="alert alert-error" role="alert">{error}</p>}
      {!data && !error && <span className="spinner" aria-label="Loading" />}
      {data && data.total === 0 && <div className="card empty"><p>No predictions yet. Your saved results will appear here.</p></div>}
      {data && data.total > 0 && (
        <>
          <div className="card table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Result</th><th>Model score</th><th><span className="sr-only">Actions</span></th></tr></thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id}>
                    <td>{fmtDate(p.created_at)}</td>
                    <td><Link to={`/predictions/${p.id}`}>{p.predicted_label}</Link></td>
                    <td>{p.model_score != null ? `${(p.model_score * 100).toFixed(1)}%` : "—"}</td>
                    <td><button className="icon-btn" aria-label={`Delete prediction ${p.id}`} onClick={() => remove(p.id)}><Trash2 size={18} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row-between">
            <button className="btn btn-outline" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - PAGE))}>Previous</button>
            <span className="muted">{skip + 1}–{Math.min(skip + PAGE, data.total)} of {data.total}</span>
            <button className="btn btn-outline" disabled={skip + PAGE >= data.total} onClick={() => setSkip(skip + PAGE)}>Next</button>
          </div>
        </>
      )}
    </div>
  );
}
