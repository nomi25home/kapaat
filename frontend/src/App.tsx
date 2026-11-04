import { createContext, useContext } from "react";
import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { ApiError, setCsrf } from "./api/client";
import { useMe } from "./api/hooks";
import type { Me } from "./api/types";
import { Icon } from "./components/Icon";
import { Loading } from "./components/ui";
import { AddPage } from "./routes/Add";
import { BinPage } from "./routes/BinPage";
import { HomePage } from "./routes/Home";
import { ItemPage } from "./routes/ItemPage";
import { LabelsPage } from "./routes/Labels";
import { LocationsPage } from "./routes/Locations";
import { LoginPage } from "./routes/Login";
import { ScanPage } from "./routes/Scan";
import { SettingsPage } from "./routes/Settings";

const MeCtx = createContext<Me | null>(null);
export const useSession = () => useContext(MeCtx)!;

function RequireAuth() {
  const { data, error, isLoading } = useMe();
  const loc = useLocation();
  if (isLoading) return <Loading />;
  if (error instanceof ApiError && error.status === 401) {
    return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />;
  }
  if (!data) return <div className="empty">Can't reach Kapaat. Check your connection and reload.</div>;
  setCsrf(data.csrf);
  return (
    <MeCtx.Provider value={data}>
      <div className="app">
        <Outlet />
        <BottomNav />
      </div>
    </MeCtx.Provider>
  );
}

function BottomNav() {
  const tab = (to: string, icon: Parameters<typeof Icon>[0]["name"], label: string, extra = "") => (
    <NavLink to={to} end={to === "/"} className={({ isActive }) => `${extra} ${isActive ? "active" : ""}`}>
      <span className="ico">
        <Icon name={icon} />
      </span>
      {label}
    </NavLink>
  );
  return (
    <nav className="bottomnav" aria-label="Main">
      {tab("/", "home", "Home")}
      {tab("/scan", "scan", "Scan")}
      {tab("/add", "plus", "Add", "add")}
      {tab("/places", "place", "Places")}
      {tab("/more", "more", "More")}
    </nav>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/scan" element={<ScanPage />} />
        <Route path="/add" element={<AddPage />} />
        <Route path="/places" element={<LocationsPage />} />
        <Route path="/labels" element={<LabelsPage />} />
        <Route path="/more" element={<SettingsPage />} />
        <Route path="/b/:code" element={<BinPage />} />
        <Route path="/i/:id" element={<ItemPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
