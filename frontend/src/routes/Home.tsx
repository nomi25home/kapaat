import { useDeferredValue, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useBins, useItems, useLocations, type ItemFilters } from "../api/hooks";
import { Icon } from "../components/Icon";
import { BinRow, ItemRow, MoveSheet } from "../components/pickers";
import { Empty, Loading } from "../components/ui";

type Filter = "all" | "unassigned" | "out" | "retired";

export function HomePage() {
  const [params, setParams] = useSearchParams();
  const view = params.get("view") === "bins" ? "bins" : "items";
  const filter = (params.get("f") as Filter) || "all";
  const roomId = params.get("room") ? Number(params.get("room")) : undefined;
  const [q, setQ] = useState(params.get("q") ?? "");
  const query = useDeferredValue(q.trim());
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [moving, setMoving] = useState(false);
  const { data: rooms = [] } = useLocations();

  const set = (k: string, v: string | null) => {
    const p = new URLSearchParams(params);
    if (v) p.set(k, v);
    else p.delete(k);
    setParams(p, { replace: true });
  };

  const itemFilters: ItemFilters = {
    q: query || undefined,
    room_id: roomId,
    unassigned: filter === "unassigned" || undefined,
    checked_out: filter === "out" || undefined,
    status: filter === "retired" ? "retired" : undefined,
  };
  const items = useItems(itemFilters, view === "items");
  const bins = useBins({
    q: query || undefined,
    room_id: roomId,
    unassigned: filter === "unassigned" || undefined,
    status: filter === "retired" ? "retired" : undefined,
  }, view === "bins");

  const toggle = (id: number) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const stopSelecting = () => {
    setSelecting(false);
    setSelected(new Set());
  };

  const chip = (value: Filter, label: string) => (
    <button className={`chip ${filter === value ? "on" : ""}`} onClick={() => set("f", value === "all" ? null : value)}>
      {label}
    </button>
  );

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <img src="/icon-192.png" alt="" /> Kapaat
        </div>
        <div className="grow" />
        {view === "items" && filter !== "retired" && (
          <button className={`btn sm ${selecting ? "primary" : ""}`} onClick={() => (selecting ? stopSelecting() : setSelecting(true))}>
            <Icon name="select" size={18} /> {selecting ? "Done" : "Select"}
          </button>
        )}
      </header>
      <main className="page" style={{ paddingBottom: selecting ? 80 : undefined }}>
        <div className="searchbar">
          <Icon name="search" size={18} />
          <input
            className="input"
            type="search"
            placeholder={view === "items" ? "Search items, tags, bins…" : "Search bins"}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search"
          />
        </div>
        <div className="segmented" role="tablist">
          <button role="tab" aria-selected={view === "items"} className={view === "items" ? "on" : ""} onClick={() => { set("view", null); stopSelecting(); }}>
            Items
          </button>
          <button role="tab" aria-selected={view === "bins"} className={view === "bins" ? "on" : ""} onClick={() => { set("view", "bins"); stopSelecting(); }}>
            Bins
          </button>
        </div>
        <div className="chips">
          {chip("all", "All")}
          {chip("unassigned", view === "items" ? "Not in a bin" : "No location")}
          {view === "items" && chip("out", "Checked out")}
          {chip("retired", "Retired")}
          {rooms.length > 0 && (
            <select
              className="chip"
              value={roomId ?? ""}
              onChange={(e) => set("room", e.target.value || null)}
              aria-label="Room"
              style={{ appearance: "auto" }}
            >
              <option value="">All rooms</option>
              {rooms.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          )}
        </div>

        {view === "items" ? (
          items.isLoading ? (
            <Loading />
          ) : (
            <section className="card list" aria-label="Items">
              {items.data?.length === 0 && (
                <Empty>
                  {query || filter !== "all" || roomId ? "Nothing matches." : <>No items yet. <Link to="/add">Add your first item</Link>.</>}
                </Empty>
              )}
              {items.data?.map((it) => (
                <ItemRow key={it.id} item={it} selectable={selecting} selected={selected.has(it.id)} onToggle={() => toggle(it.id)} />
              ))}
            </section>
          )
        ) : bins.isLoading ? (
          <Loading />
        ) : (
          <section className="card list" aria-label="Bins">
            {bins.data?.length === 0 && (
              <Empty>{query || filter !== "all" || roomId ? "Nothing matches." : <>No bins yet. <Link to="/add?type=bin">Add a bin</Link>.</>}</Empty>
            )}
            {bins.data?.map((b) => <BinRow key={b.id} bin={b} />)}
          </section>
        )}
      </main>

      {selecting && (
        <div className="selectionbar">
          <span className="grow">{selected.size} selected</span>
          <button className="btn sm" onClick={() => setSelected(new Set(items.data?.map((i) => i.id)))}>Select all</button>
          <button className="btn sm" disabled={!selected.size} onClick={() => setMoving(true)}>
            <Icon name="move" size={18} /> Move
          </button>
        </div>
      )}
      {moving && <MoveSheet itemIds={[...selected]} onClose={() => setMoving(false)} onDone={stopSelecting} />}
    </>
  );
}
