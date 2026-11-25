import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { AutocompleteService } from "../src/autocomplete-service.js";
import { createAutocompleteServer } from "../src/http/server.js";

// Real server on an ephemeral port, exercised with the built-in fetch:
// tests the full request → route → service → JSON path with no mocks.
let server: Server;
let base: string;
let service: AutocompleteService;
const onError = vi.fn();

beforeAll(async () => {
  service = new AutocompleteService({ defaultLimit: 2, maxLimit: 10, maxQueryLength: 20 });
  service.load([
    { word: "http", frequency: 9 },
    { word: "https", frequency: 7 },
    { word: "hash", frequency: 5 },
    { word: "café", frequency: 3 },
  ]);
  server = createAutocompleteServer(service, { onError });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

afterAll(async () => {
  await new Promise<void>((resolve, reject) => server.close((err) => (err ? reject(err) : resolve())));
});

const postJson = (path: string, body: string, type = "application/json"): Promise<Response> =>
  fetch(base + path, { method: "POST", headers: { "Content-Type": type }, body });

describe("HTTP API", () => {
  it("GET /health", async () => {
    const res = await fetch(`${base}/health`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok", words: 4 });
  });

  it("GET /suggest returns ranked JSON with the default limit", async () => {
    const res = await fetch(`${base}/suggest?q=H`);
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toMatch(/application\/json/);
    expect(await res.json()).toEqual({
      query: "H",
      suggestions: [
        { word: "http", frequency: 9 },
        { word: "https", frequency: 7 },
      ],
    });
  });

  it("GET /suggest honours limit and decodes unicode queries", async () => {
    const res = await fetch(`${base}/suggest?q=${encodeURIComponent("caf")}&limit=5`);
    expect((await res.json()).suggestions).toEqual([{ word: "café", frequency: 3 }]);
  });

  it.each(["abc", "0", "-1"])("GET /suggest rejects limit=%s with 400", async (limit) => {
    const res = await fetch(`${base}/suggest?q=h&limit=${limit}`);
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/limit/);
  });

  it("POST /select boosts the chosen word", async () => {
    for (let i = 0; i < 3; i++) {
      const res = await postJson("/select", JSON.stringify({ word: "hash" }));
      expect(res.status).toBe(200);
    }
    const res = await fetch(`${base}/suggest?q=ha`);
    expect((await res.json()).suggestions[0]).toEqual({ word: "hash", frequency: 8 });
  });

  it.each([
    ["not json", "application/json", 400],
    ['{"word": 5}', "application/json", 400],
    ["[]", "application/json", 400],
    ['{"word":"x"}', "text/plain", 415],
    [JSON.stringify({ word: "x".repeat(2_000) }), "application/json", 413],
  ])("POST /select rejects %j (%s) with %i", async (body, type, status) => {
    const res = await postJson("/select", body, type);
    expect(res.status).toBe(status);
    expect(await res.json()).toHaveProperty("error");
  });

  it("DELETE /words/:word removes a word, then 404s", async () => {
    service.recordSelection("temp word");
    const path = `${base}/words/${encodeURIComponent("Temp Word")}`;
    expect((await fetch(path, { method: "DELETE" })).status).toBe(204);
    expect((await fetch(path, { method: "DELETE" })).status).toBe(404);
  });

  it("DELETE rejects malformed percent-encoding with 400", async () => {
    expect((await fetch(`${base}/words/%E0%A4%A`, { method: "DELETE" })).status).toBe(400);
  });

  it("unknown paths are 404 and wrong methods are 405 with Allow", async () => {
    expect((await fetch(`${base}/nope`)).status).toBe(404);
    const res = await fetch(`${base}/suggest`, { method: "PUT" });
    expect(res.status).toBe(405);
    expect(res.headers.get("allow")).toBe("GET");
  });

  it("hides unexpected errors behind a generic 500", async () => {
    const spy = vi.spyOn(service, "suggest").mockImplementationOnce(() => {
      throw new Error("secret internal detail");
    });
    const res = await fetch(`${base}/suggest?q=h`);
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({ error: "internal server error" });
    expect(onError).toHaveBeenCalledOnce();
    spy.mockRestore();
  });
});
