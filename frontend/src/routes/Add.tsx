import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { post, upload } from "../api/client";
import { useBins, useCategories, useInvalidate } from "../api/hooks";
import type { Bin, Item } from "../api/types";
import { Icon } from "../components/Icon";
import { BinPickerSheet, TagInput, ZoneSelect } from "../components/pickers";
import { TopBar, errorText, useToast, where } from "../components/ui";

const LAST_BIN = "kapaat:last-bin";

function lastBin(): number | null {
  try {
    const v = localStorage.getItem(LAST_BIN);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function AddPage() {
  const [params, setParams] = useSearchParams();
  const type = params.get("type") === "bin" ? "bin" : "item";
  return (
    <>
      <TopBar title={type === "bin" ? "New bin" : "New item"} />
      <main className="page">
        <div className="segmented">
          <button className={type === "item" ? "on" : ""} onClick={() => setParams({}, { replace: true })}>Item</button>
          <button className={type === "bin" ? "on" : ""} onClick={() => setParams({ type: "bin" }, { replace: true })}>Bin</button>
        </div>
        {type === "item" ? <AddItem presetBin={params.get("bin")} /> : <AddBin />}
      </main>
    </>
  );
}

function AddItem({ presetBin }: { presetBin: string | null }) {
  const toast = useToast();
  const nav = useNavigate();
  const invalidate = useInvalidate();
  const { data: bins = [] } = useBins();
  const { data: categories = [] } = useCategories();
  const [name, setName] = useState("");
  const [qty, setQty] = useState(1);
  const [category, setCategory] = useState("");
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [binId, setBinId] = useState<number | null>(presetBin ? Number(presetBin) : lastBin());
  const [photo, setPhoto] = useState<File | null>(null);
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const bin = bins.find((b) => b.id === binId) ?? null;

  const save = async (e: FormEvent, again: boolean) => {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      const item = await post<Item>("/api/items", { name, qty, category, notes, tags, bin_id: bin?.id ?? null });
      if (photo) await upload(`/api/items/${item.id}/photo`, photo);
      try {
        if (bin) localStorage.setItem(LAST_BIN, String(bin.id));
        else localStorage.removeItem(LAST_BIN);
      } catch {
        /* ignore */
      }
      await invalidate();
      toast(`Added ${item.name}${bin ? ` to ${bin.code}` : ""}`);
      if (again) {
        setName("");
        setQty(1);
        setNotes("");
        setPhoto(null);
      } else {
        nav(`/i/${item.id}`);
      }
    } catch (err) {
      toast(errorText(err), "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="stack" onSubmit={(e) => save(e, false)}>
      <label className="field">
        Name
        <input className="input" required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} autoFocus placeholder="e.g. Cordless drill" />
      </label>
      <div className="grid2">
        <label className="field">
          Quantity
          <input className="input" type="number" min={0} inputMode="numeric" value={qty} onChange={(e) => setQty(Math.max(0, Number(e.target.value)))} />
        </label>
        <label className="field">
          Category
          <input className="input" list="kapaat-categories" maxLength={80} value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Optional" />
          <datalist id="kapaat-categories">
            {categories.map((c) => <option key={c} value={c} />)}
          </datalist>
        </label>
      </div>
      <div className="field">
        <span>Bin</span>
        <button type="button" className="btn" style={{ justifyContent: "flex-start" }} onClick={() => setPicking(true)}>
          <Icon name="bin" size={18} />
          {bin ? (
            <span className="ellipsis"><span className="bincode">{bin.code}</span> {bin.name} <span className="muted">{where(bin.location)}</span></span>
          ) : (
            <span className="muted">Not in a bin yet — you can put it in one later</span>
          )}
        </button>
      </div>
      <label className="field">
        Tags
        <TagInput value={tags} onChange={setTags} />
      </label>
      <label className="field">
        Notes
        <textarea className="input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
      </label>
      <label className="field">
        Photo
        <input className="input" type="file" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
      </label>
      <div className="grid2">
        <button type="button" className="btn" disabled={busy || !name.trim()} onClick={(e) => save(e, true)}>
          Save &amp; add another
        </button>
        <button className="btn primary" disabled={busy || !name.trim()}>
          Save item
        </button>
      </div>
      {picking && (
        <BinPickerSheet
          title="Put it in…"
          allowUnassign
          onClose={() => setPicking(false)}
          onPick={(b) => {
            setBinId(b?.id ?? null);
            setPicking(false);
          }}
        />
      )}
    </form>
  );
}

function AddBin() {
  const toast = useToast();
  const nav = useNavigate();
  const invalidate = useInvalidate();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [zoneId, setZoneId] = useState<number | null>(null);
  const [color, setColor] = useState("#4cd7f6");
  const [busy, setBusy] = useState(false);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const bin = await post<Bin>("/api/bins", { name, code: code.trim() || null, zone_id: zoneId, color });
      await invalidate();
      toast(`Created ${bin.code}`);
      nav(`/b/${encodeURIComponent(bin.code)}?created=1`);
    } catch (err) {
      toast(errorText(err), "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="stack" onSubmit={save}>
      <label className="field">
        Name
        <input className="input" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Camping gear" autoFocus />
      </label>
      <label className="field">
        Where is it?
        <ZoneSelect value={zoneId} onChange={setZoneId} />
      </label>
      <div className="grid2">
        <label className="field">
          Code
          <input className="input mono" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} pattern="[A-Za-z0-9][A-Za-z0-9_\-]{0,31}" placeholder="Auto (B-0001…)" />
        </label>
        <label className="field">
          Colour
          <input className="input" type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ padding: 4 }} />
        </label>
      </div>
      <button className="btn primary" disabled={busy}>
        Create bin
      </button>
      <p className="muted small" style={{ margin: 0 }}>
        You'll be able to print its label right away.
      </p>
    </form>
  );
}
