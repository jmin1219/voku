import { NavLink } from "react-router-dom";
import { Home } from "lucide-react";

export default function Sidebar() {
  return (
    <aside
      className="w-60 shrink-0 flex flex-col"
      style={{
        backgroundColor: "var(--level-2)",
        borderRight: "1px solid var(--border-dark)",
      }}
    >
      {/* Logo */}
      <div
        className="h-16 px-4 flex items-center"
        style={{ borderBottom: "1px solid var(--border-dark)" }}
      >
        <NavLink to="/" className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shadow-medium"
            style={{
              background:
                "linear-gradient(135deg, var(--finance-primary), var(--finance-secondary))",
            }}
          >
            <span
              style={{ color: "var(--level-1)" }}
              className="font-bold text-lg"
            >
              V
            </span>
          </div>
          <span
            className="font-semibold text-lg tracking-tight"
            style={{ color: "var(--text-dark-primary)" }}
          >
            Voku
          </span>
        </NavLink>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
        <NavLink
          to="/"
          end
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200"
          style={({ isActive }) =>
            isActive
              ? {
                  background:
                    "linear-gradient(to right, rgba(54, 184, 200, 0.15), rgba(42, 159, 173, 0.1))",
                  color: "var(--finance-primary)",
                }
              : { color: "var(--text-dark-secondary)" }
          }
        >
          <Home className="w-4 h-4 shrink-0" />
          <span>Home</span>
        </NavLink>
      </nav>

      {/* Version */}
      <div
        className="p-4"
        style={{ borderTop: "1px solid var(--border-dark)" }}
      >
        <div
          className="text-[10px] font-mono text-center"
          style={{ color: "var(--text-dark-muted)" }}
        >
          v0.3 • FOUNDATION
        </div>
      </div>
    </aside>
  );
}
