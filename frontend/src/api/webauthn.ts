import { post } from "./client";
import type { Me } from "./types";

const b64urlToBuf = (s: string): ArrayBuffer => {
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const bin = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0)).buffer;
};

const bufToB64url = (buf: ArrayBuffer): string =>
  btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

type Json = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export const passkeysSupported = () => typeof window !== "undefined" && !!window.PublicKeyCredential;

export async function registerPasskey(name: string): Promise<void> {
  const o: Json = await post("/api/auth/passkeys/register/options");
  const cred = (await navigator.credentials.create({
    publicKey: {
      ...o,
      challenge: b64urlToBuf(o.challenge),
      user: { ...o.user, id: b64urlToBuf(o.user.id) },
      excludeCredentials: (o.excludeCredentials ?? []).map((c: Json) => ({ ...c, id: b64urlToBuf(c.id) })),
    } as PublicKeyCredentialCreationOptions,
  })) as PublicKeyCredential | null;
  if (!cred) throw new Error("Passkey creation was cancelled");
  const r = cred.response as AuthenticatorAttestationResponse;
  await post(`/api/auth/passkeys/register?name=${encodeURIComponent(name)}`, {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      clientDataJSON: bufToB64url(r.clientDataJSON),
      attestationObject: bufToB64url(r.attestationObject),
      transports: r.getTransports?.() ?? [],
    },
    clientExtensionResults: cred.getClientExtensionResults(),
  });
}

export async function signInWithPasskey(): Promise<Me> {
  const o: Json = await post("/api/auth/passkeys/login/options");
  const cred = (await navigator.credentials.get({
    publicKey: {
      ...o,
      challenge: b64urlToBuf(o.challenge),
      allowCredentials: (o.allowCredentials ?? []).map((c: Json) => ({ ...c, id: b64urlToBuf(c.id) })),
    } as PublicKeyCredentialRequestOptions,
  })) as PublicKeyCredential | null;
  if (!cred) throw new Error("Passkey sign-in was cancelled");
  const r = cred.response as AuthenticatorAssertionResponse;
  return post<Me>("/api/auth/passkeys/login", {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      clientDataJSON: bufToB64url(r.clientDataJSON),
      authenticatorData: bufToB64url(r.authenticatorData),
      signature: bufToB64url(r.signature),
      userHandle: r.userHandle ? bufToB64url(r.userHandle) : null,
    },
    clientExtensionResults: cred.getClientExtensionResults(),
  });
}
