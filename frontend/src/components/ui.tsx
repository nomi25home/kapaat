import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "./Icon";

/* ── Toast ─────────────────────────────────────────────────────────────── */
type ToastFn = (msg: string, kind?: "ok" | "err") => void;
const ToastCtx = createContext<ToastFn>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);
  const timer = useRef<number>(0);
  const show = useCallback<ToastFn>((msg, kind = "ok") => {
    window.clearTimeout(timer.current);
    setToast({ msg, kind });
    timer.current = window.setTimeout(() => setToast(null), kind === "err" ? 5000 : 2600);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {toast && (
        <div className={`toast ${toast.kind === "err" ? "err" : ""}`} role="status" aria-live="polite">
          {toast.msg}
        </div>
      )}
    </ToastCtx.Provider>
  );
}

export function errorText(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}

/* ── Sheet (bottom sheet on phones, dialog on desktop) ─────────────────── */
export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="row nowrap spread">
          <h2>{title}</h2>
          <button className="iconbtn" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ── Page chrome ───────────────────────────────────────────────────────── */
export function TopBar({ title, back, actions }: { title: ReactNode; back?: boolean; actions?: ReactNode }) {
  const nav = useNavigate();
  return (
    <header className="topbar">
      {back && (
        <button className="iconbtn" aria-label="Back" onClick={() => (history.length > 1 ? nav(-1) : nav("/"))}>
          <Icon name="back" />
        </button>
      )}
      <h1>{title}</h1>
      {actions}
    </header>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function Loading() {
  return <div className="empty">Loading…</div>;
}

export function PhotoThumb({ photo, icon = "box" }: { photo: string | null; icon?: "box" | "bin" }) {
  return photo ? (
    <img className="thumb" src={`/api/photos/${photo}`} alt="" loading="lazy" />
  ) : (
    <span className="thumb">
      <Icon name={icon} />
    </span>
  );
}

export function where(loc: { room: string | null; zone: string | null }): string {
  return [loc.room, loc.zone].filter(Boolean).join(" › ");
}

export function fmtDate(iso: string): string {
  const d = new Date(iso);
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: sameYear ? undefined : "numeric" });
}
