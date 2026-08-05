import { unwrap, type Paginated } from "./api";

describe("unwrap", () => {
  it("passes a plain array through unchanged", () => {
    const rows = [{ id: "a" }, { id: "b" }];
    expect(unwrap(rows)).toBe(rows);
  });

  it("extracts results from a DRF page envelope", () => {
    const page: Paginated<{ id: string }> = {
      count: 40,
      next: "http://x/api/v1/threads/?page=2",
      previous: null,
      results: [{ id: "a" }],
    };
    expect(unwrap(page)).toEqual([{ id: "a" }]);
  });

  it("handles an empty envelope", () => {
    expect(unwrap({ count: 0, next: null, previous: null, results: [] })).toEqual([]);
  });
});

describe("HTML-instead-of-JSON guard", () => {
  it("rejects an HTML response with a message naming the real cause", async () => {
    const { api } = await import("./api");
    // Simulate what a static host does when a rewrite is missing: 200 OK, index.html body.
    const handler = (
      api.interceptors.response as unknown as {
        handlers: { fulfilled: (r: unknown) => unknown }[];
      }
    ).handlers.find((h) => h?.fulfilled);

    expect(() =>
      handler!.fulfilled({ headers: { "content-type": "text/html; charset=utf-8" } }),
    ).toThrow(/proxy/i);
  });

  it("passes a normal JSON response straight through", async () => {
    const { api } = await import("./api");
    const handler = (
      api.interceptors.response as unknown as {
        handlers: { fulfilled: (r: unknown) => unknown }[];
      }
    ).handlers.find((h) => h?.fulfilled);

    const response = { headers: { "content-type": "application/json" }, data: [1, 2] };
    expect(handler!.fulfilled(response)).toBe(response);
  });
});
