import { Link } from "react-router-dom";
import { ClipboardList, Cpu, History, LockKeyhole } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import Disclaimer from "../components/Disclaimer.jsx";

const features = [
  { icon: ClipboardList, title: "Structured clinical form", text: "Enter the 13 clinical measurements the model was trained on. The form is generated from the model's own schema." },
  { icon: Cpu, title: "Real ML model", text: "A tuned LightGBM classifier from the project notebook runs on the server for every prediction." },
  { icon: History, title: "Private history", text: "Each prediction is saved to your account so you can review it later. Only you can see your records." },
  { icon: LockKeyhole, title: "Secure accounts", text: "Passwords are hashed with bcrypt and sessions use signed tokens." },
];
const steps = ["Create an account", "Fill in the clinical form", "Review the model output and its limits"];

export default function LandingPage() {
  const { user } = useAuth();
  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <p className="eyebrow">Educational demo · machine learning</p>
          <h1>Explore how a model estimates heart-disease patterns</h1>
          <p className="lead">HeartWise lets you enter clinical measurements and see what a classifier trained on a small public dataset predicts. It is a learning project, not medical advice.</p>
          <div className="row">
            <Link className="btn btn-primary btn-lg" to={user ? "/predict" : "/register"}>{user ? "New prediction" : "Get started"}</Link>
            {!user && <Link className="btn btn-outline btn-lg" to="/login">Log in</Link>}
          </div>
        </div>
      </section>

      <section className="container section">
        <h2 className="section-title">What it does</h2>
        <div className="grid-4">
          {features.map(({ icon: Icon, title, text }) => (
            <article className="card" key={title}>
              <span className="icon-chip"><Icon size={22} aria-hidden /></span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="container section">
        <h2 className="section-title">How it works</h2>
        <ol className="steps">
          {steps.map((s, i) => <li key={s}><span className="step-num">{i + 1}</span>{s}</li>)}
        </ol>
      </section>

      <section className="container section"><Disclaimer /></section>
    </>
  );
}
