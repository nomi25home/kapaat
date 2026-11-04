import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { del, upload } from "../api/client";
import { itemActions, useCategories, useHistory, useInvalidate, useInventoryMutation, useItem } from "../api/hooks";
import type { HistoryEvent, Item } from "../api/types";
import { Icon } from "../components/Icon";
import { MoveSheet, TagInput } from "../components/pickers";
import { Empty, Loading, Sheet, TopBar, errorText, fmtDate, useToast, where } from "../components/ui";
import { labelUrl } from "./Labels";

const REASONS = ["Used up", "Donated", "Sold", "Thrown away", "Lost"];

export function ItemPage() {
  const id = Number(useParams().id);
  const { data: item, isLoading, error } = useItem(id);
  const history = useHistory(id);
  const [sheet, setSheet] = useState<"edit" | "move" | "checkout" | "retire" | null>(null);
  const toast = useToast();
  const invalidate = useInvalidate();
  const act = useInventoryMutation((fn: () => Promise<unknown>) => fn());

  if (isLoading) return <Loading />;
  if (error || !item)
    return (
      <>
        <TopBar title="Item" back />
        <main className="page">
          <Empty>That item doesn't exist.</Empty>
        </main>
      </>
    );

  const run = (fn: () => Promise<unknown>, ok: string) =>
    act.mutate(fn, { onSuccess: () => toast(ok), onError: (e) => toast(errorText(e), "err") });

  const active = item.status === "active";

  const setPhoto = async (file: File | undefined) => {
    if (!file) return;
    try {
      await upload(`/api/items/${item.id}/photo`, file);
      await invalidate();
      toast("Photo saved");
    } catch (e) {
      toast(errorText(e), "err");
    }
  };

  return (
    <>
      <TopBar
        back
        title={item.name}
        actions={
          active && (
            <button className="iconbtn" aria-label="Edit item" onClick={() => setSheet("edit")}>
              <Icon name="edit" />
            </button>
          )
        }
      />
      <main className="page">
        {item.photo && <img className="photo" src={`/api/photos/${item.photo}`} alt={`Photo of ${item.name}`} />}

        <section className="card pad stack">
          <div className="row">
            <span style={{ fontSize: 20, fontWeight: 700 }} className="grow">
              {item.name}
            </span>
            {item.checkout && <span className="badge out">Checked out</span>}
            {!active && <span className="badge retired">Retired</span>}
          </div>
          <dl className="kv">
            <dt>Bin</dt>
            <dd>
              {item.bin ? (
                <Link to={`/b/${encodeURIComponent(item.bin.code)}`}>
                  <span className="bincode">{item.bin.code}</span> {item.bin.name}
                </Link>
              ) : (
                <span className="muted">Not in a bin</span>
              )}
            </dd>
            <dt>Where</dt>
            <dd>{where(item.location) || <span className="muted">—</span>}</dd>
            <dt>Quantity</dt>
            <dd>{item.qty}</dd>
            {item.category && (
              <>
                <dt>Category</dt>
                <dd>{item.category}</dd>
              </>
            )}
            {item.tags.length > 0 && (
              <>
                <dt>Tags</dt>
                <dd className="row" style={{ gap: 4 }}>
                  {item.tags.map((t) => (
                    <Link key={t.id} className="tag" to={`/?q=${encodeURIComponent(t.name)}`}>
                      <span className="dot" style={{ background: t.color }} />
                      {t.name}
                    </Link>
                  ))}
                </dd>
              </>
            )}
            {item.checkout && (
              <>
                <dt>Out with</dt>
                <dd>
                  {item.checkout.user ?? "someone"} since {fmtDate(item.checkout.out_at)}
                  {item.checkout.due_at && `, due ${fmtDate(item.checkout.due_at)}`}
                  {item.checkout.note && <div className="muted small">{item.checkout.note}</div>}
                </dd>
              </>
            )}
            {!active && (
              <>
                <dt>Retired</dt>
                <dd>
                  {item.retired_at && fmtDate(item.retired_at)}
                  {item.retire_reason && ` — ${item.retire_reason}`}
                </dd>
              </>
            )}
          </dl>
          {item.notes && <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{item.notes}</p>}
        </section>

        {active ? (
          <div className="grid2">
            {item.checkout ? (
              <button className="btn primary" onClick={() => run(() => itemActions.checkin(item.id), "Checked in")}>
                <Icon name="in" size={18} /> Check in
              </button>
            ) : (
              <button className="btn primary" onClick={() => setSheet("checkout")}>
                <Icon name="out" size={18} /> Check out
              </button>
            )}
            <button className="btn" onClick={() => setSheet("move")}>
              <Icon name="move" size={18} /> Move
            </button>
            <label className="btn" style={{ cursor: "pointer" }}>
              <Icon name="camera" size={18} /> {item.photo ? "New photo" : "Add photo"}
              <input type="file" accept="image/*" capture="environment" hidden onChange={(e) => setPhoto(e.target.files?.[0])} />
            </label>
            <a className="btn" href={labelUrl([], [item.id])} target="_blank" rel="noreferrer">
              <Icon name="label" size={18} /> Label
            </a>
            {item.photo && (
              <button className="btn" onClick={() => run(() => del(`/api/items/${item.id}/photo`), "Photo removed")}>
                Remove photo
              </button>
            )}
            <button className="btn danger" disabled={!!item.checkout} title={item.checkout ? "Check it in first" : undefined} onClick={() => setSheet("retire")}>
              <Icon name="trash" size={18} /> Retire
            </button>
          </div>
        ) : (
          <button className="btn" onClick={() => run(() => itemActions.restore(item.id), "Restored")}>
            <Icon name="restore" size={18} /> Restore item
          </button>
        )}

        <h3>History</h3>
        <section className="card pad timeline">
          {history.data?.map((e) => (
            <div key={e.id}>
              <time dateTime={e.at}>{fmtDate(e.at)}</time>
              <span>{describe(e)}</span>
            </div>
          ))}
        </section>
      </main>

      {sheet === "move" && <MoveSheet itemIds={[item.id]} fromBinId={item.bin?.id} onClose={() => setSheet(null)} />}
      {sheet === "edit" && <EditItemSheet item={item} onClose={() => setSheet(null)} />}
      {sheet === "checkout" && <CheckoutSheet item={item} onClose={() => setSheet(null)} />}
      {sheet === "retire" && (
        <Sheet title={`Retire ${item.name}`} onClose={() => setSheet(null)}>
          <p className="muted small" style={{ margin: 0 }}>It will be hidden from your inventory but kept in history.</p>
          <div className="stack">
            {REASONS.map((r) => (
              <button key={r} className="btn" onClick={() => { run(() => itemActions.retire(item.id, r), `${item.name} retired`); setSheet(null); }}>
                {r}
              </button>
            ))}
          </div>
        </Sheet>
      )}
    </>
  );
}

function describe(e: HistoryEvent): string {
  const by = e.user ? ` by ${e.user}` : "";
  const p = e.payload as Record<string, string | null>;
  switch (e.action) {
    case "created":
      return `Added${p.bin ? ` to ${p.bin}` : ""}${by}${p.source ? ` (${p.source})` : ""}`;
    case "moved":
      return `Moved ${p.from ? `from ${p.from} ` : ""}${p.to ? `to ${p.to}` : "out of its bin"}${by}${p.reason ? ` (${p.reason})` : ""}`;
    case "checked_out":
      return `Checked out${by}${p.note ? ` — ${p.note}` : ""}`;
    case "checked_in":
      return `Checked in${by}`;
    case "retired":
      return `Retired${by}${p.reason ? ` — ${p.reason}` : ""}`;
    case "restored":
      return `Restored${by}`;
    case "photo_updated":
      return `Photo updated${by}`;
    case "v1_history":
      return `Kapaat v1: ${p.action}${p.details ? ` — ${p.details}` : ""}${p.actor ? ` by ${p.actor}` : ""}`;
    default:
      return `Edited${by}`;
  }
}

function EditItemSheet({ item, onClose }: { item: Item; onClose: () => void }) {
  const [name, setName] = useState(item.name);
  const [qty, setQty] = useState(item.qty);
  const [category, setCategory] = useState(item.category);
  const [notes, setNotes] = useState(item.notes);
  const [tags, setTags] = useState(item.tags.map((t) => t.name));
  const { data: categories = [] } = useCategories();
  const toast = useToast();
  const save = useInventoryMutation(() => itemActions.update(item.id, { name, qty, category, notes, tags }));
  return (
    <Sheet title="Edit item" onClose={onClose}>
      <label className="field">
        Name
        <input className="input" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} />
      </label>
      <div className="grid2">
        <label className="field">
          Quantity
          <input className="input" type="number" min={0} value={qty} onChange={(e) => setQty(Math.max(0, Number(e.target.value)))} />
        </label>
        <label className="field">
          Category
          <input className="input" list="kapaat-cat-edit" value={category} onChange={(e) => setCategory(e.target.value)} />
          <datalist id="kapaat-cat-edit">{categories.map((c) => <option key={c} value={c} />)}</datalist>
        </label>
      </div>
      <label className="field">
        Tags
        <TagInput value={tags} onChange={setTags} />
      </label>
      <label className="field">
        Notes
        <textarea className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <button
        className="btn primary"
        disabled={!name.trim() || save.isPending}
        onClick={() => save.mutate(undefined, { onSuccess: () => { toast("Saved"); onClose(); }, onError: (e) => toast(errorText(e), "err") })}
      >
        Save
      </button>
    </Sheet>
  );
}

function CheckoutSheet({ item, onClose }: { item: Item; onClose: () => void }) {
  const [due, setDue] = useState("");
  const [note, setNote] = useState("");
  const toast = useToast();
  const go = useInventoryMutation(() =>
    itemActions.checkout(item.id, { due_at: due ? new Date(`${due}T23:59:00`).toISOString() : null, note }),
  );
  return (
    <Sheet title={`Check out ${item.name}`} onClose={onClose}>
      <label className="field">
        Due back (optional)
        <input className="input" type="date" value={due} onChange={(e) => setDue(e.target.value)} />
      </label>
      <label className="field">
        Note (optional)
        <input className="input" maxLength={300} placeholder="e.g. lent to Sam" value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <button
        className="btn primary"
        disabled={go.isPending}
        onClick={() => go.mutate(undefined, { onSuccess: () => { toast("Checked out"); onClose(); }, onError: (e) => toast(errorText(e), "err") })}
      >
        Check out
      </button>
    </Sheet>
  );
}
