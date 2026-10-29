import { ShieldAlert } from "lucide-react";

export default function Disclaimer({ text }) {
  return (
    <div className="disclaimer" role="note">
      <ShieldAlert size={20} aria-hidden />
      <p>{text || "Educational demonstration only. Results come from a machine-learning model trained on a small public dataset. They are not a medical diagnosis, may be inaccurate, and do not replace a qualified healthcare professional. If you have chest pain, shortness of breath, fainting or other emergency symptoms, seek urgent medical care immediately."}</p>
    </div>
  );
}
