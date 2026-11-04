import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { patch, post, upload } from "../api/client";
import { useBinByCode, useBins, useInvalidate, useItems } from "../api/hooks";
import type { Bin } from "../api/types";
import { Icon } from "../components/Icon";
import { BinList, ItemRow, MoveSheet, ZoneSelect } from "../components/pickers";
import { Empty, Loading, Sheet, TopBar, errorText, fmtDate, useToast, where } from "../components/ui";
import { labelUrl } from "./Labels";

export function BinPage() {
  const { code = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const { data: bin, error, isLoading } = useBinByCode(code);
  const items = useItems({ bin_id: bin?.id }, !!bin);
  const [sheet, setSheet] = useState<"edit" | "retire" | "move" | null>(null);
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const invalidate = useInvalidate();
  const toast = useToast();

  if (isLoading) return <Loading />;
  if (error || !bin)
    return (
      <>
        <TopBar title={code} back />
        <main className="page">
          <Empty>
            No bin with code <b className="bincode">{code}</b>. <Link to={`/add?type=bin`}>Create a bin</Link>
          </Empty>
        </main>
      </>
    );

  const active = bin.status === "active";
  const toggle = (id: number) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const setPhoto = async (file: File | undefined) => {
    if (!file) return;
    try {
      await upload(`/api/bins/${bin.id}/photo`, file);
      await invalidate();
      toast("Photo saved");
    } catch (e) {
      toast(errorText(e), "err");
    }
  };

  const restore = async () => {
    try {
      await post(`/api/bins/${bin.id}/restore`);
      await invalidate();
      toast(`${bin.code} is back in use`);
    } catch (e) {
      toast(errorText(e), "err");
    }
  };

  return (
    <>
      <TopBar
        back
        title={<span className="bincode">{bin.code}</span>}
        actions={
          active && (
            <button className="iconbtn" aria-label="Edit bin" onClick={() => setSheet("edit")}>
              <Icon name="edit" />
            </button>
          )
        }
      />
      <main className="page" style={{ paddingBottom: selecting ? 80 : undefined }}>
        {params.get("created") && (
          <div className="card pad row" style={{ background: "var(--primary-soft)" }}>
            <span className="grow">Bin created. Print its label and stick it on.</span>
            <a className="btn primary sm" href={labelUrl([bin.id])} target="_blank" rel="noreferrer" onClick={() => setParams({}, { replace: true })}>
              <Icon name="label" size={18} /> Print label
            </a>
          </div>
        )}

        <section className="card pad stack">
          <div className="row nowrap">
            <span className="swatch" style={{ background: bin.color, width: 18, height: 18 }} />
            <div className="grow">
              <div style={{ fontSize: 20, fontWeight: 700 }}>{bin.name || <span className="muted">Unnamed bin</span>}</div>
              <div className="muted">{where(bin.location) || "No location set"}</div>
            </div>
            {!active && <span className="badge retired">Retired</span>}
          </div>
          {bin.photo && <img className="photo" src={`/api/photos/${bin.photo}`} alt={`Photo of ${bin.code}`} />}
          {bin.notes && <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{bin.notes}</p>}
          {!active && (
            <p className="muted small" style={{ margin: 0 }}>
              Retired {bin.retired_at && fmtDate(bin.retired_at)}
              {bin.retire_reason && ` — ${bin.retire_reason}`}
            </p>
          )}
          <div className="row">
            {active ? (
              <>
                <Link className="btn primary sm" to={`/add?bin=${bin.id}`}>
                  <Icon name="plus" size={18} /> Add item here
                </Link>
                <a className="btn sm" href={labelUrl([bin.id])} target="_blank" rel="noreferrer">
                  <Icon name="label" size={18} /> Label
                </a>
                <label className="btn sm" style={{ cursor: "pointer" }}>
                  <Icon name="camera" size={18} /> Photo
                  <input type="file" accept="image/*" capture="environment" hidden onChange={(e) => setPhoto(e.target.files?.[0])} />
                </label>
                <button className="btn sm danger" onClick={() => setSheet("retire")}>
                  <Icon name="trash" size={18} /> Retire
                </button>
              </>
            ) : (
              <button className="btn sm" onClick={restore}>
                <Icon name="restore" size={18} /> Restore bin
              </button>
            )}
          </div>
        </section>

        <div className="row spread">
          <h3>Contents · {items.data?.length ?? 0}</h3>
          {active && !!items.data?.length && (
            <button className={`btn sm ${selecting ? "primary" : "ghost"}`} onClick={() => { setSelecting(!selecting); setSelected(new Set()); }}>
              {selecting ? "Done" : "Select"}
            </button>
          )}
        </div>
        <section className="card list">
          {items.isLoading && <Loading />}
          {items.data?.length === 0 && <Empty>This bin is empty.</Empty>}
          {items.data?.map((it) => (
            <ItemRow key={it.id} item={it} showBin={false} selectable={selecting} selected={selected.has(it.id)} onToggle={() => toggle(it.id)} />
          ))}
        </section>
      </main>

      {selecting && (
        <div className="selectionbar">
          <span className="grow">{selected.size} selected</span>
          <button className="btn sm" onClick={() => setSelected(new Set(items.data?.map((i) => i.id)))}>Select all</button>
          <button className="btn sm" disabled={!selected.size} onClick={() => setSheet("move")}>
            <Icon name="move" size={18} /> Move
          </button>
        </div>
      )}
      {sheet === "move" && (
        <MoveSheet itemIds={[...selected]} fromBinId={bin.id} onClose={() => setSheet(null)} onDone={() => { setSelecting(false); setSelected(new Set()); }} />
      )}
      {sheet === "edit" && <EditBinSheet bin={bin} onClose={() => setSheet(null)} />}
      {sheet === "retire" && <RetireBinSheet bin={bin} onClose={() => setSheet(null)} />}
    </>
  );
}

function EditBinSheet({ bin, onClose }: { bin: Bin; onClose: () => void }) {
  const [name, setName] = useState(bin.name);
  const [zoneId, setZoneId] = useState(bin.location.zone_id);
  const [color, setColor] = useState(bin.color);
  const [notes, setNotes] = useState(bin.notes);
  const invalidate = useInvalidate();
  const toast = useToast();
  const save = async () => {
    try {
      await patch(`/api/bins/${bin.id}`, { name, color, notes, zone_id: zoneId, clear_zone: zoneId === null });
      await invalidate();
      toast("Saved");
      onClose();
    } catch (e) {
      toast(errorText(e), "err");
    }
  };
  return (
    <Sheet title={`Edit ${bin.code}`} onClose={onClose}>
      <label className="field">
        Name
        <input className="input" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="field">
        Location
        <ZoneSelect value={zoneId} onChange={setZoneId} />
      </label>
      <label className="field">
        Colour
        <input className="input" type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ padding: 4 }} />
      </label>
      <label className="field">
        Notes
        <textarea className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <button className="btn primary" onClick={save}>Save</button>
    </Sheet>
  );
}

function RetireBinSheet({ bin, onClose }: { bin: Bin; onClose: () => void }) {
  const invalidate = useInvalidate();
  const toast = useToast();
  const [reason, setReason] = useState("");
  const [contents, setContents] = useState<"unassign" | "move">("unassign");
  const [target, setTarget] = useState<Bin | null>(null);
  const { data: bins = [] } = useBins();

  const retire = async () => {
    try {
      await post(`/api/bins/${bin.id}/retire`, { reason, contents, target_bin_id: target?.id ?? null });
      await invalidate();
      toast(`${bin.code} retired`);
      onClose();
    } catch (e) {
      toast(errorText(e), "err");
    }
  };

  return (
    <Sheet title={`Retire ${bin.code}`} onClose={onClose}>
      <p className="muted small" style={{ margin: 0 }}>
        Retired bins disappear from lists but keep their history. You can restore them later.
      </p>
      <label className="field">
        Reason
        <input className="input" placeholder="e.g. broken, repurposed" value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} />
      </label>
      {bin.item_count > 0 && (
        <div className="stack">
          <div className="field"><span>What happens to its {bin.item_count} item{bin.item_count === 1 ? "" : "s"}?</span></div>
          <div className="segmented">
            <button className={contents === "unassign" ? "on" : ""} onClick={() => setContents("unassign")}>Take out of bin</button>
            <button className={contents === "move" ? "on" : ""} onClick={() => setContents("move")}>Move to another bin</button>
          </div>
          {contents === "move" &&
            (target ? (
              <button className="btn" onClick={() => setTarget(null)}>
                Moving to <span className="bincode">{target.code}</span> {target.name} — change
              </button>
            ) : (
              <BinList bins={bins} exclude={bin.id} onPick={setTarget} />
            ))}
        </div>
      )}
      <button className="btn danger" disabled={contents === "move" && bin.item_count > 0 && !target} onClick={retire}>
        Retire bin
      </button>
    </Sheet>
  );
}
