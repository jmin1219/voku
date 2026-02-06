import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Shell() {
  return (
    <div
      className="h-screen w-screen grid grid-cols-[auto_1fr] overflow-hidden"
      style={{ backgroundColor: "var(--level-1)" }}
    >
      <Sidebar />
      <main className="overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
