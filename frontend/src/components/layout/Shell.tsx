import { Outlet, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import Sidebar from "./Sidebar";

export default function Shell() {
  const location = useLocation();
  
  // Determine domain based on route
  const domain = location.pathname.startsWith('/fitness') 
    ? 'fitness' 
    : location.pathname.startsWith('/finance')
    ? 'finance'
    : 'home';

  return (
    <div className="h-screen w-screen grid grid-cols-[auto_1fr] overflow-hidden" style={{ backgroundColor: 'var(--level-1)' }}>
      {/* Sidebar */}
      <Sidebar />

      {/* Main content area with layered domain aesthetic (gradient + grid) */}
      <div className={cn(
        "grid grid-rows-[1fr] overflow-hidden",
        domain === 'fitness' && "section-fitness bg-grid-fitness",
        domain === 'finance' && "section-finance bg-grid-finance",
        domain === 'home' && "bg-grid"
      )}>
        <main className="overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
