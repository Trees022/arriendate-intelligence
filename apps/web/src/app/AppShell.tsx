import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { to: "/dashboard", label: "Dashboard", glyph: "⌂" },
  { to: "/properties", label: "Propiedades", glyph: "◇" },
  { to: "/publications", label: "Publicaciones", glyph: "↗" },
  { to: "/inbox", label: "Inbox", glyph: "◎" },
  { to: "/leads", label: "Leads", glyph: "◌" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to="/dashboard" aria-label="Arriendate, inicio">
          <span className="brand__mark" aria-hidden="true">AI</span>
          <span>
            <strong>Arriendate</strong>
            <small>Operaciones</small>
          </span>
        </NavLink>

        <nav className="navigation" aria-label="Navegación principal">
          <p className="navigation__label">Operación</p>
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `navigation__item${isActive ? " is-active" : ""}`}
            >
              <span className="navigation__glyph" aria-hidden="true">{item.glyph}</span>
              {item.label}
            </NavLink>
          ))}
          <NavLink className="sidebar-create" to="/properties/new">+ Nueva propiedad</NavLink>
        </nav>

        <div className="sidebar__footer">
          <span className="system-dot" aria-hidden="true" />
          <div>
            <strong>Demo local</strong>
            <small>Datos ficticios</small>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <div className="mobile-brand">
          <span className="brand__mark" aria-hidden="true">AI</span>
          <strong>Arriendate</strong>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
