import { describe, expect, it } from "vitest";
import { parseScan } from "./Scan";

describe("parseScan", () => {
  it("reads v2 bin and item labels", () => {
    expect(parseScan("https://kapaat.home/b/B-0042")).toEqual({ kind: "bin", code: "B-0042" });
    expect(parseScan("https://kapaat.home/i/17")).toEqual({ kind: "item", id: 17 });
  });

  it("reads v1 labels so old stickers keep working", () => {
    expect(parseScan("http://192.168.1.5:8099/bin/GARAGE-1")).toEqual({ kind: "bin", code: "GARAGE-1" });
    expect(parseScan("http://192.168.1.5:8099/scan/GARAGE-1")).toEqual({ kind: "bin", code: "GARAGE-1" });
  });

  it("accepts a typed bin code and decodes escapes", () => {
    expect(parseScan(" tools-2 ")).toEqual({ kind: "bin", code: "tools-2" });
    expect(parseScan("https://x/b/A%2DB")).toEqual({ kind: "bin", code: "A-B" });
  });

  it("rejects unrelated QR codes", () => {
    expect(parseScan("https://example.com/menu")).toBeNull();
    expect(parseScan("WIFI:S:home;T:WPA;P:secret;;")).toBeNull();
  });
});
