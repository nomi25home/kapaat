import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { get } from "../api/client";
import { itemActions, useInvalidate } from "../api/hooks";
import type { Bin, Item } from "../api/types";
import { Icon } from "../components/Icon";
import { TopBar, errorText, useToast } from "../components/ui";

type Mode = "open" | "move" | "checkin";
export type Scanned = { kind: "bin"; code: string } | { kind: "item"; id: number } | null;

export function parseScan(text: string): Scanned {
  const t = text.trim();
  let path = t;
  try {
    path = new URL(t).pathname;
  } catch {
    /* not a URL: treat as a bare code */
  }
  const bin = path.match(/^\/b\/([^/?#]+)/);
  if (bin) return { kind: "bin", code: decodeURIComponent(bin[1]) };
  const item = path.match(/^\/i\/(\d+)/);
  if (item) return { kind: "item", id: Number(item[1]) };
  // v1 labels pointed at /bin/{id} and /scan/{id}
  const legacy = path.match(/^\/(?:bin|scan)\/([^/?#]+)/);
  if (legacy) return { kind: "bin", code: decodeURIComponent(legacy[1]) };
  if (/^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/.test(t)) return { kind: "bin", code: t };
  return null;
}

function useCamera(onText: (text: string) => void, enabled: boolean) {
  const video = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState("");
  const last = useRef({ text: "", at: 0 });
  const cb = useRef(onText);
  cb.current = onText;

  useEffect(() => {
    if (!enabled || !video.current) return;
    let controls: { stop: () => void } | undefined;
    let cancelled = false;
    (async () => {
      try {
        const { BrowserQRCodeReader } = await import("@zxing/browser");
        const reader = new BrowserQRCodeReader(undefined, { delayBetweenScanAttempts: 150 });
        const c = await reader.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" } } },
          video.current!,
          (result) => {
            if (!result) return;
            const text = result.getText();
            const now = Date.now();
            if (text === last.current.text && now - last.current.at < 2500) return;
            last.current = { text, at: now };
            navigator.vibrate?.(40);
            cb.current(text);
          },
        );
        if (cancelled) c.stop();
        else controls = c;
      } catch (e) {
        setError(
          e instanceof DOMException && e.name === "NotAllowedError"
            ? "Camera permission was denied. Allow camera access, or type a bin code below."
            : "Couldn't start the camera. Type a bin code below instead.",
        );
      }
    })();
    return () => {
      cancelled = true;
      controls?.stop();
    };
  }, [enabled]);

  return { video, error };
}

export function ScanPage() {
  const nav = useNavigate();
  const toast = useToast();
  const invalidate = useInvalidate();
  const [mode, setMode] = useState<Mode>("open");
  const [basket, setBasket] = useState<Item[]>([]);
  const [manual, setManual] = useState("");
  const [busy, setBusy] = useState(false);

  const handle = useCallback(
    async (text: string) => {
      const s = parseScan(text);
      if (!s) {
        toast("That QR code isn't a Kapaat label", "err");
        return;
      }
      if (mode === "open") {
        nav(s.kind === "bin" ? `/b/${encodeURIComponent(s.code)}` : `/i/${s.id}`);
        return;
      }
      setBusy(true);
      try {
        if (s.kind === "item") {
          const item = await get<Item>(`/api/items/${s.id}`);
          if (mode === "checkin") {
            if (!item.checkout) toast(`${item.name} wasn't checked out`);
            else {
              await itemActions.checkin(item.id);
              await invalidate();
              toast(`Checked in ${item.name}`);
            }
          } else {
            setBasket((b) => (b.some((x) => x.id === item.id) ? b : [...b, item]));
            toast(`Added ${item.name}`);
          }
        } else if (mode === "move") {
          const bin = await get<Bin>(`/api/bins/by-code/${encodeURIComponent(s.code)}`);
          if (!basket.length) {
            toast("Scan the items first, then the bin they're going into", "err");
          } else {
            await itemActions.move(basket.map((i) => i.id), bin.id);
            await invalidate();
            toast(`Moved ${basket.length} item${basket.length === 1 ? "" : "s"} to ${bin.code}`);
            setBasket([]);
          }
        } else {
          toast("Scan an item label to check it in", "err");
        }
      } catch (e) {
        toast(errorText(e), "err");
      } finally {
        setBusy(false);
      }
    },
    [mode, basket, nav, toast, invalidate],
  );

  const { video, error } = useCamera(handle, true);

  const submitManual = (e: FormEvent) => {
    e.preventDefault();
    if (manual.trim()) handle(manual.trim());
    setManual("");
  };

  return (
    <>
      <TopBar title="Scan" />
      <main className="page">
        <div className="segmented">
          <button className={mode === "open" ? "on" : ""} onClick={() => setMode("open")}>Open</button>
          <button className={mode === "move" ? "on" : ""} onClick={() => setMode("move")}>Move into bin</button>
          <button className={mode === "checkin" ? "on" : ""} onClick={() => setMode("checkin")}>Check in</button>
        </div>
        <p className="muted small" style={{ margin: 0 }}>
          {mode === "open" && "Point at a bin or item label to open it."}
          {mode === "move" && "Scan item labels to collect them, then scan the bin they're going into."}
          {mode === "checkin" && "Scan item labels to check each one back in."}
        </p>
        <div className="scanner" aria-busy={busy}>
          <video ref={video} muted playsInline />
          <div className="frame" />
        </div>
        {error && <div className="error">{error}</div>}

        {mode === "move" && basket.length > 0 && (
          <section className="card pad stack">
            <div className="row spread">
              <b>{basket.length} item{basket.length === 1 ? "" : "s"} ready to move</b>
              <button className="btn sm ghost" onClick={() => setBasket([])}>Clear</button>
            </div>
            <div className="row">
              {basket.map((i) => (
                <span key={i.id} className="tag">{i.name}</span>
              ))}
            </div>
          </section>
        )}

        <form className="row nowrap" onSubmit={submitManual}>
          <input className="input mono" placeholder="Or type a bin code, e.g. B-0012" value={manual} onChange={(e) => setManual(e.target.value)} aria-label="Bin code" />
          <button className="btn" aria-label="Go"><Icon name="move" size={18} /></button>
        </form>
      </main>
    </>
  );
}
