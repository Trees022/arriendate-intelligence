import { Link } from "react-router-dom";
import { StatePanel } from "../components/StatePanel";

export function NotFoundPage() {
  return (
    <div className="page-stack compact-page">
      <StatePanel title="Página no encontrada" message="La ruta solicitada no existe en este workspace." />
      <Link className="button button--primary button--fit" to="/dashboard">Volver al dashboard</Link>
    </div>
  );
}
