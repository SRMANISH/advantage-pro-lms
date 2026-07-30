import { act, render, renderHook, screen } from "@testing-library/react";

import { Paginator, useTableTools } from "./TableTools";

const people = [
  { name: "Asha Rao", batch: "FS-1" },
  { name: "Ravi Kumar", batch: "FS-1" },
  { name: "Meena Iyer", batch: "DA-2" },
];

describe("useTableTools", () => {
  it("filters rows across the given keys, case-insensitively", () => {
    const { result } = renderHook(() => useTableTools(people, ["name", "batch"], 10));
    act(() => result.current.setQuery("da-2"));
    expect(result.current.rows).toEqual([{ name: "Meena Iyer", batch: "DA-2" }]);
    expect(result.current.total).toBe(1);
  });

  it("paginates and resets to page 1 when the query changes", () => {
    const { result } = renderHook(() => useTableTools(people, ["name"], 2));
    expect(result.current.pageCount).toBe(2);
    act(() => result.current.setPage(2));
    expect(result.current.rows).toEqual([{ name: "Meena Iyer", batch: "DA-2" }]);
    act(() => result.current.setQuery("a"));
    expect(result.current.page).toBe(1);
  });

  it("clamps the page when the filtered list shrinks", () => {
    const { result } = renderHook(() => useTableTools(people, ["name"], 1));
    act(() => result.current.setPage(3));
    expect(result.current.page).toBe(3);
    act(() => result.current.setQuery("asha"));
    expect(result.current.page).toBe(1);
    expect(result.current.rows).toEqual([{ name: "Asha Rao", batch: "FS-1" }]);
  });

  it("tolerates undefined rows while data loads", () => {
    const { result } = renderHook(() => useTableTools(undefined, ["name" as never], 10));
    expect(result.current.rows).toEqual([]);
    expect(result.current.pageCount).toBe(1);
  });
});

describe("Paginator", () => {
  it("renders nothing for a single page", () => {
    const { container } = render(<Paginator page={1} pageCount={1} onPage={() => undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("disables Prev on the first page and Next on the last", () => {
    const { rerender } = render(
      <Paginator page={1} pageCount={3} onPage={() => undefined} total={25} />,
    );
    expect(screen.getByRole("button", { name: "← Prev" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next →" })).toBeEnabled();
    rerender(<Paginator page={3} pageCount={3} onPage={() => undefined} total={25} />);
    expect(screen.getByRole("button", { name: "Next →" })).toBeDisabled();
  });
});
