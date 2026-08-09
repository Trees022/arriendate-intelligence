import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { to: "/dashboard", label: "Dashboard", glyph: "⌂" },
  { to: "/leads/new", label: "Nuevo lead", glyph: "+" },
  { to: "/properties", label: "Propiedades", glyph: "◇" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to="/dashboard" aria-label="Arriendate Intelligence, inicio">
          <span className="brand__mark" aria-hidden="true">AI</span>
          <span>
            <strong>Arriendate</strong>
            <small>Intelligence</small>
          </span>
        </NavLink>

        <nav className="navigation" aria-label="Navegación principal">
          <p className="navigation__label">Workspace</p>
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
        </nav>

        <div className="sidebar__footer">
          <span className="system-dot" aria-hidden="true" />
          <div>
            <strong>Demo local</strong>
            <small>Datos 100% sintéticos</small>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <div className="mobile-brand">
          <span className="brand__mark" aria-hidden="true">AI</span>
          <strong>Arriendate Intelligence</strong>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
