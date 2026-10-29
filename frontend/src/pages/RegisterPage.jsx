import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = "Name is required.";
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Enter a valid email address.";
    if (form.password.length < 8) e.password = "Password must be at least 8 characters.";
    else if (new TextEncoder().encode(form.password).length > 72) e.password = "Password must be at most 72 bytes.";
    if (form.confirm !== form.password) e.confirm = "Passwords do not match.";
    return e;
  }

  async function onSubmit(ev) {
    ev.preventDefault();
    if (busy) return;
    setError("");
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      await register(form.name.trim(), form.email.trim(), form.password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      if (err.fieldErrors) setErrors(err.fieldErrors);
      setError(err.message);
      setBusy(false);
    }
  }

  const field = (id, label, type, auto) => (
    <>
      <label htmlFor={id}>{label}</label>
      <input id={id} type={type} autoComplete={auto} value={form[id]} onChange={set(id)} aria-invalid={!!errors[id]} aria-describedby={errors[id] ? id + "-err" : undefined} />
      {errors[id] && <span className="field-error" id={id + "-err"}>{errors[id]}</span>}
    </>
  );

  return (
    <div className="container auth-wrap">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <h1>Create account</h1>
        {error && <p className="alert alert-error" role="alert">{error}</p>}
        {field("name", "Name", "text", "name")}
        {field("email", "Email", "email", "email")}
        {field("password", "Password (min. 8 characters)", "password", "new-password")}
        {field("confirm", "Confirm password", "password", "new-password")}
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
        <p className="muted">Already registered? <Link to="/login">Log in</Link></p>
      </form>
    </div>
  );
}
