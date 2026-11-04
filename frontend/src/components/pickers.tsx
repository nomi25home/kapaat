import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { itemActions, useBins, useInventoryMutation, useLocations, useTags } from "../api/hooks";
import type { Bin, Item } from "../api/types";
import { Icon } from "./Icon";
import { Empty, PhotoThumb, Sheet, errorText, useToast, where } from "./ui";

export function ZoneSelect({
  value,
  onChange,
  id,
}: {
  value: number | null;
  onChange: (zoneId: number | null) => void;
  id?: string;
}) {
  const { data: rooms = [] } = useLocations();
  return (
    <select id={id} className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
      <option value="">No location yet</option>
      {rooms.map((r) => (
        <optgroup key={r.id} label={r.name}>
          {r.zones.map((z) => (
            <option key={z.id} value={z.id}>
              {r.name} › {z.name}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

export function BinList({ bins, onPick, exclude }: { bins: Bin[]; onPick: (b: Bin) => void; exclude?: number | null }) {
  const [q, setQ] = useState("");
  const shown = useMemo(() => {
    const s = q.trim().toLowerCase();
    return bins.filter(
      (b) => b.id !== exclude && (!s || `${b.code} ${b.name} ${where(b.location)}`.toLowerCase().includes(s)),
    );
  }, [bins, q, exclude]);
  return (
    <div className="stack">
      <input className="input" placeholder="Search bins" value={q} onChange={(e) => setQ(e.target.value)} autoFocus />
      <div className="card list" style={{ maxHeight: "50dvh", overflow: "auto" }}>
        {shown.length === 0 && <Empty>No bins match.</Empty>}
        {shown.map((b) => (
          <button key={b.id} className="li" style={{ border: 0, background: "none", textAlign: "left", width: "100%", cursor: "pointer" }} onClick={() => onPick(b)}>
            <span className="swatch" style={{ background: b.color }} />
            <div className="grow">
              <div>
                <span className="bincode">{b.code}</span> {b.name}
              </div>
              <div className="muted small">{where(b.location) || "No location"} · {b.item_count} items</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function BinPickerSheet({
  title,
  onPick,
  onClose,
  allowUnassign,
  exclude,
}: {
  title: string;
  onPick: (b: Bin | null) => void;
  onClose: () => void;
  allowUnassign?: boolean;
  exclude?: number | null;
}) {
  const { data: bins = [] } = useBins();
  return (
    <Sheet title={title} onClose={onClose}>
      {allowUnassign && (
        <button className="btn" onClick={() => onPick(null)}>
          Take out of bin (unassigned)
        </button>
      )}
      <BinList bins={bins} onPick={onPick} exclude={exclude} />
    </Sheet>
  );
}

export function MoveSheet({ itemIds, fromBinId, onDone, onClose }: { itemIds: number[]; fromBinId?: number | null; onDone?: () => void; onClose: () => void }) {
  const toast = useToast();
  const move = useInventoryMutation(({ bin }: { bin: Bin | null }) => itemActions.move(itemIds, bin?.id ?? null));
  return (
    <BinPickerSheet
      title={`Move ${itemIds.length} item${itemIds.length === 1 ? "" : "s"} to…`}
      allowUnassign
      exclude={fromBinId}
      onClose={onClose}
      onPick={(bin) =>
        move.mutate(
          { bin },
          {
            onSuccess: () => {
              toast(bin ? `Moved to ${bin.code}` : "Taken out of bin");
              onDone?.();
              onClose();
            },
            onError: (e) => toast(errorText(e), "err"),
          },
        )
      }
    />
  );
}

export function TagInput({ value, onChange }: { value: string[]; onChange: (tags: string[]) => void }) {
  const { data: tags = [] } = useTags();
  const [draft, setDraft] = useState("");
  const add = (raw: string) => {
    const names = raw.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean);
    if (names.length) onChange([...new Set([...value, ...names])]);
    setDraft("");
  };
  return (
    <div className="stack" style={{ gap: 6 }}>
      {value.length > 0 && (
        <div className="row">
          {value.map((t) => (
            <button key={t} type="button" className="tag" style={{ border: 0, cursor: "pointer" }} onClick={() => onChange(value.filter((x) => x !== t))} aria-label={`Remove tag ${t}`}>
              {t} <Icon name="close" size={12} />
            </button>
          ))}
        </div>
      )}
      <input
        className="input"
        list="kapaat-tags"
        placeholder="Add tags (Enter or comma)"
        value={draft}
        onChange={(e) => (e.target.value.endsWith(",") ? add(e.target.value) : setDraft(e.target.value))}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            add(draft);
          }
        }}
        onBlur={() => draft && add(draft)}
      />
      <datalist id="kapaat-tags">
        {tags.map((t) => (
          <option key={t.id} value={t.name} />
        ))}
      </datalist>
    </div>
  );
}

export function ItemRow({
  item,
  selectable,
  selected,
  onToggle,
  showBin = true,
}: {
  item: Item;
  selectable?: boolean;
  selected?: boolean;
  onToggle?: () => void;
  showBin?: boolean;
}) {
  const body = (
    <>
      {selectable && <input type="checkbox" checked={!!selected} onChange={onToggle} aria-label={`Select ${item.name}`} onClick={(e) => e.stopPropagation()} />}
      <PhotoThumb photo={item.photo} />
      <div className="grow">
        <div className="row nowrap" style={{ gap: 6 }}>
          <span className="ellipsis" style={{ fontWeight: 600 }}>{item.name}</span>
          {item.qty !== 1 && <span className="muted small">×{item.qty}</span>}
        </div>
        <div className="muted small ellipsis">
          {showBin && (item.bin ? <span className="bincode">{item.bin.code}</span> : "Unassigned")}
          {showBin && where(item.location) && ` · ${where(item.location)}`}
          {!showBin && (item.category || item.tags.map((t) => t.name).join(", "))}
        </div>
      </div>
      {item.checkout && <span className="badge out">Out</span>}
      {item.status === "retired" && <span className="badge retired">Retired</span>}
    </>
  );
  return selectable ? (
    <label className="li" style={{ cursor: "pointer" }}>{body}</label>
  ) : (
    <Link className="li" to={`/i/${item.id}`}>{body}</Link>
  );
}

export function BinRow({ bin }: { bin: Bin }) {
  return (
    <Link className="li" to={`/b/${encodeURIComponent(bin.code)}`}>
      <PhotoThumb photo={bin.photo} icon="bin" />
      <div className="grow">
        <div className="row nowrap" style={{ gap: 6 }}>
          <span className="swatch" style={{ background: bin.color }} />
          <span className="bincode">{bin.code}</span>
          <span className="ellipsis">{bin.name}</span>
        </div>
        <div className="muted small ellipsis">
          {where(bin.location) || "No location"} · {bin.item_count} item{bin.item_count === 1 ? "" : "s"}
        </div>
      </div>
      {bin.status === "retired" && <span className="badge retired">Retired</span>}
    </Link>
  );
}
