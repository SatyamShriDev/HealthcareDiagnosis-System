import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { fmtDate } from "../components/ResultCard.jsx";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="container page narrow">
      <h1>Profile</h1>
      <div className="card">
        <dl className="inputs">
          <div><dt>Name</dt><dd>{user.name}</dd></div>
          <div><dt>Email</dt><dd>{user.email}</dd></div>
          <div><dt>Member since</dt><dd>{fmtDate(user.created_at)}</dd></div>
        </dl>
        <button className="btn btn-outline" onClick={() => { logout(); navigate("/"); }}>Log out</button>
      </div>
      <p className="muted small">Your session token is kept only in this browser tab (sessionStorage) and is removed when you log out or close the tab.</p>
    </div>
  );
}
