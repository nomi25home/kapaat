import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { post, setCsrf } from "../api/client";
import { keys, useFeatures } from "../api/hooks";
import type { Me } from "../api/types";
import { passkeysSupported, signInWithPasskey } from "../api/webauthn";
import { errorText } from "../components/ui";

const SSO_ERRORS: Record<string, string> = {
  sso_failed: "Single sign-on failed. Try again.",
  sso_no_email: "Your identity provider didn't share a verified email.",
  not_invited: "That account hasn't been invited to this Kapaat yet. Ask an admin.",
  not_allowed: "This account is disabled.",
};

export function LoginPage() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { data: features } = useFeatures();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState(() => {
    try {
      return localStorage.getItem("kapaat:email") ?? "";
    } catch {
      return "";
    }
  });
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(SSO_ERRORS[params.get("error") ?? ""] ?? "");

  const next = params.get("next")?.startsWith("/") && !params.get("next")?.startsWith("//") ? params.get("next")! : "/";

  const done = (me: Me) => {
    setCsrf(me.csrf);
    qc.setQueryData(keys.me, me);
    nav(next, { replace: true });
  };

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const requestCode = (e?: FormEvent) => {
    e?.preventDefault();
    run(async () => {
      await post("/api/auth/request-code", { email });
      try {
        localStorage.setItem("kapaat:email", email);
      } catch {
        /* storage may be unavailable */
      }
      setStep("code");
    });
  };

  const verify = (e: FormEvent) => {
    e.preventDefault();
    run(async () => done(await post<Me>("/api/auth/verify", { email, code })));
  };

  return (
    <main className="login">
      <div className="card">
        <div className="row nowrap">
          <img className="logo" src="/icon-192.png" alt="" />
          <div>
            <div style={{ fontWeight: 800, fontSize: 22 }}>Kapaat</div>
            <div className="muted small">Know what's in every bin.</div>
          </div>
        </div>

        {step === "email" ? (
          <form className="stack" onSubmit={requestCode}>
            <label className="field">
              Email
              <input className="input" type="email" autoComplete="email webauthn" required value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
            </label>
            <button className="btn primary" disabled={busy}>
              Email me a sign-in code
            </button>
          </form>
        ) : (
          <form className="stack" onSubmit={verify}>
            <p className="small" style={{ margin: 0 }}>
              If <b>{email}</b> can use this Kapaat, a 6-digit code is on its way. It expires in 10 minutes.
            </p>
            <label className="field">
              Code
              <input className="input otp" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} autoFocus />
            </label>
            <button className="btn primary" disabled={busy || code.length !== 6}>
              Sign in
            </button>
            <div className="row spread">
              <button type="button" className="btn ghost sm" onClick={() => { setStep("email"); setCode(""); }}>
                Use another email
              </button>
              <button type="button" className="btn ghost sm" disabled={busy} onClick={() => requestCode()}>
                Resend code
              </button>
            </div>
          </form>
        )}

        {error && <div className="error" role="alert">{error}</div>}

        {(features?.passkeys || features?.oidc) && <div className="divider">or</div>}
        {features?.passkeys && passkeysSupported() && (
          <button className="btn" disabled={busy} onClick={() => run(async () => done(await signInWithPasskey()))}>
            Sign in with a passkey
          </button>
        )}
        {features?.oidc && (
          <a className="btn" href="/api/auth/oidc/login">
            Continue with {features.oidc_name}
          </a>
        )}
      </div>
    </main>
  );
}
