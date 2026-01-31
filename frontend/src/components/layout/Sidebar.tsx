import { NavLink, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  Home,
  ClipboardList,
  History,
  Upload,
  List,
  PieChart,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

type NavSingleItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

type NavGroupItem = {
  label: string;
  items: NavSingleItem[];
};

type NavItem = NavSingleItem | NavGroupItem;

const navItems: NavItem[] = [
  {
    label: "Home",
    href: "/",
    icon: Home,
  },
  {
    label: "Fitness",
    items: [
      { label: "Log", href: "/fitness/log", icon: ClipboardList },
      { label: "History", href: "/fitness/history", icon: History },
    ],
  },
  {
    label: "Finance",
    items: [
      { label: "Import", href: "/finance/import", icon: Upload },
      { label: "Transactions", href: "/finance/transactions", icon: List },
      { label: "Summary", href: "/finance/summary", icon: PieChart },
    ],
  },
];

function isNavSingleItem(item: NavItem): item is NavSingleItem {
  return "href" in item;
}

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 flex flex-col" style={{ 
      backgroundColor: 'var(--level-2)', 
      borderRight: '1px solid var(--border-dark)' 
    }}>
      {/* Logo */}
      <div className="h-16 px-4 flex items-center" style={{ borderBottom: '1px solid var(--border-dark)' }}>
        <NavLink to="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center shadow-medium" 
               style={{ background: 'linear-gradient(135deg, var(--finance-primary), var(--finance-secondary))' }}>
            <span style={{ color: 'var(--level-1)' }} className="font-bold text-lg">V</span>
          </div>
          <span className="font-semibold text-lg tracking-tight" style={{ color: 'var(--text-dark-primary)' }}>Voku</span>
        </NavLink>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-3 space-y-8 overflow-y-auto">
        {navItems.map((section) =>
          isNavSingleItem(section) ? (
            <NavItemLink
              key={section.href}
              href={section.href}
              icon={section.icon}
              label={section.label}
            />
          ) : (
            <div key={section.label}>
              <div className="px-3 mb-3 text-[10px] font-semibold uppercase tracking-[0.2em]" 
                   style={{ color: 'var(--text-dark-muted)' }}>
                {section.label}
              </div>
              <div className="space-y-1">
                {section.items.map((item) => (
                  <NavItemLink
                    key={item.href}
                    href={item.href}
                    icon={item.icon}
                    label={item.label}
                  />
                ))}
              </div>
            </div>
          )
        )}
      </nav>

      {/* Version badge */}
      <div className="p-4" style={{ borderTop: '1px solid var(--border-dark)' }}>
        <div className="text-[10px] font-mono text-center" style={{ color: 'var(--text-dark-muted)' }}>
          v0.2+ • WORKSHOP
        </div>
      </div>
    </aside>
  );
}

function NavItemLink({
  href,
  icon: Icon,
  label,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
}) {
  // Determine domain from href
  const domain = href.startsWith('/fitness') 
    ? 'fitness' 
    : href.startsWith('/finance')
    ? 'finance'
    : 'home';

  return (
    <NavLink
      to={href}
      end={href === "/"}
      className={({ isActive }) => {
        const baseClasses = "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200";
        
        if (isActive && domain === 'fitness') {
          return `${baseClasses} border-2`;
        } else if (isActive && domain === 'finance') {
          return `${baseClasses} border-2`;
        } else if (isActive && domain === 'home') {
          return `${baseClasses} border-2`;
        }
        return `${baseClasses}`;
      }}
      style={({ isActive }) => {
        if (isActive && domain === 'fitness') {
          return {
            background: 'linear-gradient(to right, rgba(230, 119, 58, 0.15), rgba(212, 98, 42, 0.1))',
            color: 'var(--fitness-primary)',
            borderColor: 'rgba(230, 119, 58, 0.4)',
            boxShadow: '0 0 20px -8px rgba(230, 119, 58, 0.3)'
          };
        } else if (isActive && domain === 'finance') {
          return {
            background: 'linear-gradient(to right, rgba(54, 184, 200, 0.15), rgba(42, 159, 173, 0.1))',
            color: 'var(--finance-primary)',
            borderColor: 'rgba(54, 184, 200, 0.4)',
            boxShadow: '0 0 20px -8px rgba(54, 184, 200, 0.3)'
          };
        } else if (isActive && domain === 'home') {
          return {
            background: 'linear-gradient(to right, rgba(54, 184, 200, 0.15), rgba(42, 159, 173, 0.1))',
            color: 'var(--finance-primary)',
            borderColor: 'rgba(54, 184, 200, 0.4)',
            boxShadow: '0 0 20px -8px rgba(54, 184, 200, 0.3)'
          };
        }
        return {
          color: 'var(--text-dark-secondary)'
        };
      }}
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span>{label}</span>
    </NavLink>
  );
}
