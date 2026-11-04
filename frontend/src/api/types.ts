export type Role = "admin" | "member";

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Features {
  oidc: boolean;
  oidc_name: string;
  passkeys: boolean;
}

export interface Me {
  user: User;
  csrf: string;
  features: Features;
}

export interface Location {
  room_id: number | null;
  room: string | null;
  zone_id: number | null;
  zone: string | null;
}

export interface Zone {
  id: number;
  room_id: number;
  name: string;
  bin_count: number;
}

export interface Room {
  id: number;
  name: string;
  notes: string;
  zones: Zone[];
}

export type Status = "active" | "retired";

export interface Bin {
  id: number;
  code: string;
  name: string;
  color: string;
  notes: string;
  photo: string | null;
  status: Status;
  created_at: string;
  retired_at: string | null;
  retire_reason: string;
  location: Location;
  item_count: number;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
  item_count?: number;
}

export interface Checkout {
  id: number;
  item_id: number;
  user: string | null;
  out_at: string;
  due_at: string | null;
  in_at: string | null;
  note: string;
}

export interface Item {
  id: number;
  name: string;
  category: string;
  qty: number;
  notes: string;
  photo: string | null;
  status: Status;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  retire_reason: string;
  bin: { id: number; code: string; name: string; color: string } | null;
  location: Location;
  tags: Tag[];
  checkout: Checkout | null;
}

export interface HistoryEvent {
  id: number;
  at: string;
  user: string | null;
  entity: string;
  entity_id: number;
  action: string;
  payload: Record<string, unknown>;
}

export interface LabelPreset {
  id: string;
  name: string;
  description: string;
  label_w: number;
  label_h: number;
  per_page: number;
  page: [number, number];
  crop_marks: boolean;
}

export interface ApiToken {
  id: number;
  name: string;
  scope: "read" | "write";
  created_at: string;
  last_used_at: string | null;
  token?: string;
}

export interface WebhookStatus {
  url: string;
  enabled: boolean;
  secret: string;
  pending: number;
  last_error: string;
  failed: { id: number; event: string; at: string; error: string }[];
}
