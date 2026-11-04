import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { del, get, patch, post, put } from "../api/client";
import type { ApiToken, User, WebhookStatus } from "../api/types";
import { passkeysSupported, registerPasskey } from "../api/webauthn";
import { useSession } from "../App";
import { Icon } from "../components/Icon";
import { Sheet, TopBar, errorText, fmtDate, useToast } from "../components/ui";

export function SettingsPage() {
  const { user, features } = useSession();
  const nav = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();

  const logout = async () => {
    await post("/api/auth/logout").catch(() => undefined);
    // The service worker keeps inventory for offline reading; don't leave it behind on a shared device.
    await globalThis.caches?.delete("kapaat-api").catch(() => undefined);
    qc.clear();
    nav("/login", { replace: true });
  };

  return (
    <>
      <TopBar title="More" />
      <main className="page">
        <section className="card list">
          <Link className="li" to="/labels"><Icon name="label" /> <span className="grow">Print labels</span></Link>
          <a className="li" href="/api/export/items.csv"><Icon name="download" /> <span className="grow">Export items (CSV)</span></a>
        </section>

        <Profile user={user} />
        {features.passkeys && <Passkeys />}
        <Tokens />
        {user.role === "admin" && <Users me={user} />}
        {user.role === "admin" && <Webhook />}

        <button className="btn" onClick={() => logout().catch((e) => toast(errorText(e), "err"))}>
          <Icon name="logout" size={18} /> Sign out
        </button>
        <p className="muted small" style={{ textAlign: "center", margin: 0 }}>Kapaat 2.0 · <a href="/api/docs">API docs</a></p>
      </main>
    </>
  );
}

function Section({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <>
      <div className="row spread">
        <h3>{title}</h3>
        {action}
      </div>
      <section className="card pad stack">{children}</section>
    </>
  );
}

function Profile({ user }: { user: User }) {
  const [name, setName] = useState(user.name);
  const qc = useQueryClient();
  const toast = useToast();
  return (
    <Section title="You">
      <div className="muted small">{user.email} · {user.role}</div>
      <div className="row nowrap">
        <input className="input" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} aria-label="Display name" />
        <button
          className="btn"
          disabled={name === user.name}
          onClick={() =>
            patch("/api/me", { name })
              .then(() => qc.invalidateQueries({ queryKey: ["me"] }))
              .then(() => toast("Saved"))
              .catch((e) => toast(errorText(e), "err"))
          }
        >
          Save
        </button>
      </div>
    </Section>
  );
}

function Passkeys() {
  const toast = useToast();
  const { data = [], refetch } = useQuery({ queryKey: ["passkeys"], queryFn: () => get<{ id: number; name: string; created_at: string }[]>("/api/auth/passkeys") });
  const add = async () => {
    try {
      await registerPasskey(navigator.platform ? `Passkey (${navigator.platform})` : "Passkey");
      await refetch();
      toast("Passkey added");
    } catch (e) {
      toast(errorText(e), "err");
    }
  };
  return (
    <Section title="Passkeys" action={passkeysSupported() && <button className="btn sm" onClick={add}><Icon name="key" size={16} /> Add</button>}>
      {data.length === 0 && <div className="muted small">Add a passkey to sign in with Face ID, Touch ID, or your device PIN instead of an email code.</div>}
      {data.map((p) => (
        <div key={p.id} className="row nowrap">
          <span className="grow">{p.name} <span className="muted small">· {fmtDate(p.created_at)}</span></span>
          <button className="iconbtn" aria-label={`Remove ${p.name}`} onClick={() => del(`/api/auth/passkeys/${p.id}`).then(() => refetch())}>
            <Icon name="trash" size={18} />
          </button>
        </div>
      ))}
    </Section>
  );
}

function Tokens() {
  const toast = useToast();
  const { data = [], refetch } = useQuery({ queryKey: ["tokens"], queryFn: () => get<ApiToken[]>("/api/tokens") });
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"read" | "write">("read");
  const [created, setCreated] = useState<string | null>(null);
  const create = async () => {
    try {
      const t = await post<ApiToken>("/api/tokens", { name, scope });
      setCreated(t.token ?? null);
      setName("");
      await refetch();
    } catch (e) {
      toast(errorText(e), "err");
    }
  };
  return (
    <Section title="API tokens" action={<button className="btn sm" onClick={() => setCreating(true)}><Icon name="plus" size={16} /> New</button>}>
      {data.length === 0 && <div className="muted small">Tokens let scripts and home-automation tools use the Kapaat API.</div>}
      {data.map((t) => (
        <div key={t.id} className="row nowrap">
          <span className="grow">{t.name} <span className="muted small">· {t.scope} · {t.last_used_at ? `used ${fmtDate(t.last_used_at)}` : "never used"}</span></span>
          <button className="iconbtn" aria-label={`Revoke ${t.name}`} onClick={() => del(`/api/tokens/${t.id}`).then(() => refetch())}>
            <Icon name="trash" size={18} />
          </button>
        </div>
      ))}
      {creating && (
        <Sheet title="New API token" onClose={() => { setCreating(false); setCreated(null); }}>
          {created ? (
            <>
              <p className="small" style={{ margin: 0 }}>Copy this token now — it won't be shown again.</p>
              <code className="input mono" style={{ overflowWrap: "anywhere", userSelect: "all" }}>{created}</code>
              <button className="btn primary" onClick={() => navigator.clipboard?.writeText(created).then(() => toast("Copied"), () => undefined)}>Copy</button>
            </>
          ) : (
            <>
              <label className="field">Name<input className="input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} placeholder="e.g. Home Assistant" /></label>
              <div className="segmented">
                <button className={scope === "read" ? "on" : ""} onClick={() => setScope("read")}>Read only</button>
                <button className={scope === "write" ? "on" : ""} onClick={() => setScope("write")}>Read &amp; write</button>
              </div>
              <button className="btn primary" disabled={!name.trim()} onClick={create}>Create token</button>
            </>
          )}
        </Sheet>
      )}
    </Section>
  );
}

function Users({ me }: { me: User }) {
  const toast = useToast();
  const { data = [], refetch } = useQuery({ queryKey: ["users"], queryFn: () => get<User[]>("/api/users") });
  const [email, setEmail] = useState("");
  const invite = async () => {
    try {
      await post("/api/users", { email, role: "member" });
      setEmail("");
      await refetch();
      toast("Invited. They can sign in with their email now.");
    } catch (e) {
      toast(errorText(e), "err");
    }
  };
  const update = (u: User, body: Partial<User>) =>
    patch(`/api/users/${u.id}`, body).then(() => refetch(), (e) => toast(errorText(e), "err"));
  return (
    <Section title="People">
      {data.map((u) => (
        <div key={u.id} className="row nowrap">
          <Icon name="users" size={18} />
          <span className="grow ellipsis" style={{ opacity: u.active ? 1 : 0.5 }}>
            {u.name || u.email} <span className="muted small">{u.email}</span>
          </span>
          <select className="chip" value={u.role} disabled={u.id === me.id} onChange={(e) => update(u, { role: e.target.value as User["role"] })} aria-label={`Role for ${u.email}`}>
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
          {u.id !== me.id && (
            <button className="btn sm ghost" onClick={() => update(u, { active: !u.active })}>{u.active ? "Disable" : "Enable"}</button>
          )}
        </div>
      ))}
      <form className="row nowrap" onSubmit={(e) => { e.preventDefault(); invite(); }}>
        <input className="input" type="email" placeholder="Invite by email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <button className="btn">Invite</button>
      </form>
    </Section>
  );
}

function Webhook() {
  const toast = useToast();
  const { data, refetch } = useQuery({ queryKey: ["webhook"], queryFn: () => get<WebhookStatus>("/api/settings/webhook") });
  const [url, setUrl] = useState<string | null>(null);
  if (!data) return null;
  const value = url ?? data.url;
  const save = (body: object) =>
    put<WebhookStatus>("/api/settings/webhook", { url: value, enabled: data.enabled, ...body })
      .then(() => refetch())
      .then(() => toast("Saved"))
      .catch((e) => toast(errorText(e), "err"));
  const action = (path: string, ok: (r: Record<string, unknown>) => string) =>
    post<Record<string, unknown>>(path)
      .then((r) => { toast(ok(r), r.ok === false ? "err" : "ok"); return refetch(); })
      .catch((e) => toast(errorText(e), "err"));
  return (
    <Section title="Google Sheets / webhook">
      <p className="muted small" style={{ margin: 0 }}>
        Kapaat can POST every change to a URL — a Google Apps Script that writes to a sheet, n8n, Home Assistant, or anything else.
        See <a href="https://github.com/nomi25home/kapaat/blob/main/docs/sheets-webhook.md" target="_blank" rel="noreferrer">the Sheets setup guide</a>.
      </p>
      <label className="field">
        URL
        <input className="input" type="url" placeholder="https://script.google.com/macros/s/…/exec?key=…" value={value} onChange={(e) => setUrl(e.target.value)} />
      </label>
      {data.secret && (
        <label className="field">
          Signing secret (X-Kapaat-Signature)
          <code className="input mono small" style={{ overflowWrap: "anywhere", userSelect: "all" }}>{data.secret}</code>
        </label>
      )}
      <div className="row">
        <button className="btn sm" onClick={() => save({})}>Save URL</button>
        <button className={`btn sm ${data.enabled ? "" : "primary"}`} disabled={!value} onClick={() => save({ enabled: !data.enabled })}>
          {data.enabled ? "Turn off" : "Turn on"}
        </button>
        <button className="btn sm" disabled={!value} onClick={() => action("/api/settings/webhook/test", (r) => (r.ok ? "Test delivered" : `Test failed: ${r.error || r.status}`))}>Send test</button>
        <button className="btn sm" disabled={!data.enabled} onClick={() => action("/api/settings/webhook/snapshot", (r) => `Queued snapshot of ${r.items} items`)}>Send full snapshot</button>
        <button className="btn sm ghost" onClick={() => save({ regenerate_secret: true })}>New secret</button>
      </div>
      <div className="small muted">
        {data.enabled ? "On" : "Off"} · {data.pending} waiting
        {data.last_error && ` · last error: ${data.last_error}`}
      </div>
      {data.failed.length > 0 && (
        <div className="stack small">
          <div className="error">{data.failed.length} event(s) gave up after repeated failures.</div>
          <button className="btn sm" onClick={() => action("/api/settings/webhook/retry", (r) => `Retrying ${r.requeued}`)}>Retry them</button>
        </div>
      )}
    </Section>
  );
}
