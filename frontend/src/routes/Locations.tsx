import { useState } from "react";
import { Link } from "react-router-dom";
import { del, patch, post } from "../api/client";
import { useInvalidate, useLocations } from "../api/hooks";
import type { Room, Zone } from "../api/types";
import { Icon } from "../components/Icon";
import { Empty, Loading, Sheet, TopBar, errorText, useToast } from "../components/ui";

type Editing =
  | { kind: "room"; room?: Room }
  | { kind: "zone"; roomId: number; zone?: Zone };

export function LocationsPage() {
  const { data: rooms, isLoading } = useLocations();
  const [editing, setEditing] = useState<Editing | null>(null);

  return (
    <>
      <TopBar
        title="Places"
        actions={
          <Link className="btn sm" to="/labels">
            <Icon name="label" size={18} /> Labels
          </Link>
        }
      />
      <main className="page">
        <p className="muted small" style={{ margin: 0 }}>
          Rooms are areas of your home. Zones are parts of a room — a wall, a shelf unit, a closet. Bins live in zones.
        </p>
        {isLoading && <Loading />}
        {rooms?.length === 0 && <Empty>No rooms yet. Add one to start organising bins.</Empty>}
        {rooms?.map((r) => (
          <section key={r.id} className="card">
            <div className="li" style={{ minHeight: 52 }}>
              <Icon name="place" />
              <Link className="grow" to={`/?view=bins&room=${r.id}`} style={{ color: "inherit", fontWeight: 700 }}>
                {r.name}
              </Link>
              <button className="iconbtn" aria-label={`Edit ${r.name}`} onClick={() => setEditing({ kind: "room", room: r })}>
                <Icon name="edit" size={18} />
              </button>
            </div>
            <div className="list" style={{ borderTop: "1px solid var(--line)" }}>
              {r.zones.map((z) => (
                <div key={z.id} className="li" style={{ minHeight: 48, paddingLeft: 48 }}>
                  <span className="grow">
                    {z.name} <span className="muted small">· {z.bin_count} bin{z.bin_count === 1 ? "" : "s"}</span>
                  </span>
                  <button className="iconbtn" aria-label={`Edit ${z.name}`} onClick={() => setEditing({ kind: "zone", roomId: r.id, zone: z })}>
                    <Icon name="edit" size={18} />
                  </button>
                </div>
              ))}
              <button className="li btn ghost" style={{ justifyContent: "flex-start", paddingLeft: 48, borderRadius: 0 }} onClick={() => setEditing({ kind: "zone", roomId: r.id })}>
                <Icon name="plus" size={18} /> Add zone
              </button>
            </div>
          </section>
        ))}
        <button className="btn" onClick={() => setEditing({ kind: "room" })}>
          <Icon name="plus" size={18} /> Add room
        </button>
      </main>
      {editing && <EditSheet editing={editing} rooms={rooms ?? []} onClose={() => setEditing(null)} />}
    </>
  );
}

function EditSheet({ editing, rooms, onClose }: { editing: Editing; rooms: Room[]; onClose: () => void }) {
  const isRoom = editing.kind === "room";
  const existing = isRoom ? editing.room : editing.zone;
  const [name, setName] = useState(existing?.name ?? "");
  const [roomId, setRoomId] = useState(editing.kind === "zone" ? editing.roomId : 0);
  const invalidate = useInvalidate();
  const toast = useToast();

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      await invalidate();
      toast(ok);
      onClose();
    } catch (e) {
      toast(errorText(e), "err");
    }
  };

  const save = () =>
    run(
      () =>
        isRoom
          ? existing
            ? patch(`/api/rooms/${existing.id}`, { name, notes: (existing as Room).notes })
            : post("/api/rooms", { name })
          : existing
            ? patch(`/api/zones/${existing.id}`, { name, room_id: roomId })
            : post("/api/zones", { name, room_id: roomId }),
      "Saved",
    );

  const remove = () => existing && run(() => del(`/api/${isRoom ? "rooms" : "zones"}/${existing.id}`), "Deleted");

  return (
    <Sheet title={`${existing ? "Edit" : "New"} ${isRoom ? "room" : "zone"}`} onClose={onClose}>
      <label className="field">
        Name
        <input className="input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} autoFocus placeholder={isRoom ? "e.g. Garage" : "e.g. North wall shelves"} />
      </label>
      {!isRoom && existing && (
        <label className="field">
          Room
          <select className="input" value={roomId} onChange={(e) => setRoomId(Number(e.target.value))}>
            {rooms.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </label>
      )}
      <button className="btn primary" disabled={!name.trim()} onClick={save}>Save</button>
      {existing && <button className="btn danger" onClick={remove}>Delete</button>}
    </Sheet>
  );
}
