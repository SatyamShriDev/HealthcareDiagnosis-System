import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, LogOut, Menu, X } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  const cls = ({ isActive }) => "nav-link" + (isActive ? " active" : "");

  return (
    <>
      <a href="#main" className="skip-link">Skip to content</a>
      <header className="navbar">
        <div className="container navbar-inner">
          <Link to="/" className="brand" onClick={close}><Activity size={22} aria-hidden /> HeartWise</Link>
          <button className="icon-btn nav-toggle" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
          <nav className={"nav" + (open ? " open" : "")} aria-label="Main">
            {user ? (
              <>
                <NavLink to="/dashboard" className={cls} onClick={close}>Dashboard</NavLink>
                <NavLink to="/predict" className={cls} onClick={close}>New prediction</NavLink>
                <NavLink to="/history" className={cls} onClick={close}>History</NavLink>
                <NavLink to="/profile" className={cls} onClick={close}>Profile</NavLink>
                <button className="btn btn-ghost" onClick={() => { logout(); close(); navigate("/"); }}><LogOut size={16} /> Log out</button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={cls} onClick={close}>Log in</NavLink>
                <Link to="/register" className="btn btn-primary" onClick={close}>Get started</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main id="main"><Outlet /></main>
      <footer className="footer">
        <div className="container">
          <p><strong>Educational demonstration only.</strong> Not a medical device or diagnosis. Always consult a qualified healthcare professional. In an emergency, call your local emergency number.</p>
          <p className="muted">HeartWise · college project</p>
        </div>
      </footer>
    </>
  );
}
