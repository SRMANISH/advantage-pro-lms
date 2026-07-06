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
