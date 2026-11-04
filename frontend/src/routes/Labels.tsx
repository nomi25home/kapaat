import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { qs } from "../api/client";
import { useBins, useLocations, usePresets } from "../api/hooks";
import { Icon } from "../components/Icon";
import { Empty, Loading, TopBar, where } from "../components/ui";

const PRESET_KEY = "kapaat:label-preset";

function savedPreset(): string | undefined {
  try {
    return localStorage.getItem(PRESET_KEY) ?? undefined;
  } catch {
    return undefined;
  }
}

export function labelUrl(binIds: number[], itemIds: number[] = [], opts: { preset?: string; start?: number; copies?: number } = {}) {
  return `/api/labels/pdf${qs({
    bins: binIds.join(","),
    items: itemIds.join(","),
    preset: opts.preset ?? savedPreset(),
    start: opts.start || undefined,
    copies: opts.copies && opts.copies > 1 ? opts.copies : undefined,
  })}`;
}

export function LabelsPage() {
  const [params] = useSearchParams();
  const { data: presetData } = usePresets();
  const { data: bins, isLoading } = useBins();
  const { data: rooms = [] } = useLocations();
  const [preset, setPreset] = useState<string | undefined>(savedPreset());
  const [roomId, setRoomId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set((params.get("bins") ?? "").split(",").filter(Boolean).map(Number)),
  );
  const [start, setStart] = useState(0);
  const [copies, setCopies] = useState(1);

  const current = presetData?.presets.find((p) => p.id === (preset ?? presetData.default)) ?? presetData?.presets[0];
  const shown = useMemo(() => (bins ?? []).filter((b) => roomId === null || b.location.room_id === roomId), [bins, roomId]);

  const choose = (id: string) => {
    setPreset(id);
    setStart(0);
    try {
      localStorage.setItem(PRESET_KEY, id);
    } catch {
      /* ignore */
    }
  };
  const toggle = (id: number) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const ids = (bins ?? []).filter((b) => selected.has(b.id)).map((b) => b.id);
  const url = current ? labelUrl(ids, [], { preset: current.id, start, copies }) : "#";
  const scale = 1.1;

  return (
    <>
      <TopBar back title="Print labels" />
      <main className="page">
        <h3>Label size</h3>
        <section className="card list">
          {presetData?.presets.map((p) => (
            <label key={p.id} className="preset">
              <input type="radio" name="preset" checked={current?.id === p.id} onChange={() => choose(p.id)} />
              <span className="shape" style={{ width: p.label_w * scale, height: p.label_h * scale }} aria-hidden="true" />
              <span className="grow">
                <b>{p.name}</b>
                <div className="muted small">{p.description}</div>
              </span>
            </label>
          ))}
        </section>

        {current && current.per_page > 1 && (
          <div className="grid2">
            <label className="field">
              Skip used positions on the first sheet
              <input className="input" type="number" min={0} max={current.per_page - 1} value={start} onChange={(e) => setStart(Math.min(current.per_page - 1, Math.max(0, Number(e.target.value))))} />
            </label>
            <label className="field">
              Copies of each label
              <input className="input" type="number" min={1} max={20} value={copies} onChange={(e) => setCopies(Math.min(20, Math.max(1, Number(e.target.value))))} />
            </label>
          </div>
        )}

        <div className="row spread">
          <h3>Bins · {selected.size} selected</h3>
          <div className="row">
            {rooms.length > 0 && (
              <select className="chip" value={roomId ?? ""} onChange={(e) => setRoomId(e.target.value ? Number(e.target.value) : null)} aria-label="Room">
                <option value="">All rooms</option>
                {rooms.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            )}
            <button className="btn sm ghost" onClick={() => setSelected(new Set([...selected, ...shown.map((b) => b.id)]))}>All</button>
            <button className="btn sm ghost" onClick={() => setSelected(new Set())}>None</button>
          </div>
        </div>
        <section className="card list">
          {isLoading && <Loading />}
          {bins?.length === 0 && <Empty>No bins yet.</Empty>}
          {shown.map((b) => (
            <label key={b.id} className="li" style={{ cursor: "pointer" }}>
              <input type="checkbox" checked={selected.has(b.id)} onChange={() => toggle(b.id)} />
              <span className="swatch" style={{ background: b.color }} />
              <span className="grow">
                <span className="bincode">{b.code}</span> {b.name}
                <div className="muted small">{where(b.location) || "No location"}</div>
              </span>
            </label>
          ))}
        </section>

        <a className={`btn primary block ${ids.length ? "" : "disabled"}`} aria-disabled={!ids.length} href={ids.length ? url : undefined} target="_blank" rel="noreferrer">
          <Icon name="download" size={18} /> Open printable PDF ({ids.length * copies} label{ids.length * copies === 1 ? "" : "s"})
        </a>
        <p className="muted small" style={{ margin: 0 }}>
          Print at <b>100% / actual size</b> (turn off “fit to page”). On plain paper, cut along the crop marks. The 48 mm label fits under
          standard 48 mm clear packing tape to protect it from tears and moisture.
        </p>
      </main>
    </>
  );
}
