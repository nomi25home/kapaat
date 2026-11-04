import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { get, patch, post, qs } from "./client";
import type { Bin, Features, HistoryEvent, Item, LabelPreset, Me, Room, Tag } from "./types";

export const keys = {
  me: ["me"] as const,
  items: (p: object) => ["items", p] as const,
  item: (id: number) => ["item", id] as const,
  bins: (p: object) => ["bins", p] as const,
  locations: ["locations"] as const,
  tags: ["tags"] as const,
};

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: () => get<Me>("/api/auth/me"), retry: false, staleTime: 60_000 });
}

export function useFeatures() {
  return useQuery({ queryKey: ["features"], queryFn: () => get<Features>("/api/auth/features"), staleTime: Infinity });
}

export interface ItemFilters {
  q?: string;
  status?: "active" | "retired";
  room_id?: number;
  zone_id?: number;
  bin_id?: number;
  tag?: string;
  checked_out?: boolean;
  unassigned?: boolean;
}

export function useItems(f: ItemFilters, enabled = true) {
  return useQuery({ queryKey: keys.items(f), queryFn: () => get<Item[]>(`/api/items${qs({ ...f })}`), enabled });
}

export function useItem(id: number) {
  return useQuery({ queryKey: keys.item(id), queryFn: () => get<Item>(`/api/items/${id}`) });
}

export function useHistory(id: number) {
  return useQuery({ queryKey: ["history", id], queryFn: () => get<HistoryEvent[]>(`/api/items/${id}/history`) });
}

export interface BinFilters {
  q?: string;
  status?: "active" | "retired";
  room_id?: number;
  zone_id?: number;
  unassigned?: boolean;
}

export function useBins(f: BinFilters = {}, enabled = true) {
  return useQuery({ queryKey: keys.bins(f), queryFn: () => get<Bin[]>(`/api/bins${qs({ ...f })}`), enabled });
}

export function useBinByCode(code: string) {
  return useQuery({ queryKey: ["bin", code.toUpperCase()], queryFn: () => get<Bin>(`/api/bins/by-code/${encodeURIComponent(code)}`) });
}

export function useLocations() {
  return useQuery({ queryKey: keys.locations, queryFn: () => get<Room[]>("/api/locations") });
}

export function useTags() {
  return useQuery({ queryKey: keys.tags, queryFn: () => get<Tag[]>("/api/tags") });
}

export function useCategories() {
  return useQuery({ queryKey: ["categories"], queryFn: () => get<string[]>("/api/categories") });
}

export function usePresets() {
  return useQuery({
    queryKey: ["presets"],
    queryFn: () => get<{ default: string; presets: LabelPreset[] }>("/api/labels/presets"),
    staleTime: Infinity,
  });
}

/** Any inventory write invalidates everything inventory-shaped; the dataset is small enough. */
export function useInvalidate() {
  const qc = useQueryClient();
  return () =>
    Promise.all(
      ["items", "item", "bins", "bin", "locations", "tags", "history", "categories", "checkouts"].map((k) =>
        qc.invalidateQueries({ queryKey: [k] }),
      ),
    );
}

export function useInventoryMutation<TVars, TResult>(fn: (v: TVars) => Promise<TResult>) {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: fn, onSuccess: () => invalidate() });
}

export const itemActions = {
  move: (item_ids: number[], bin_id: number | null) => post<Item[]>("/api/items/move", { item_ids, bin_id }),
  checkout: (id: number, body: { due_at?: string | null; note?: string }) => post<Item>(`/api/items/${id}/checkout`, body),
  checkin: (id: number) => post<Item>(`/api/items/${id}/checkin`),
  retire: (id: number, reason: string) => post<Item>(`/api/items/${id}/retire`, { reason }),
  restore: (id: number) => post<Item>(`/api/items/${id}/restore`),
  update: (id: number, body: Partial<Pick<Item, "name" | "category" | "qty" | "notes">> & { tags?: string[] }) =>
    patch<Item>(`/api/items/${id}`, body),
};
