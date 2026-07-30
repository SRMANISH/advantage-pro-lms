import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "./Badge";

/**
 * Badges render raw backend enum values, which arrive lowercase. This has to be a real text
 * change rather than a CSS `text-transform`: the previous `capitalize` class left the DOM text
 * lowercase, so screen readers announced "active" and copying a badge yielded "active" — and it
 * Title-Cased every word, turning "awaiting grade" into "Awaiting Grade".
 */
describe("Badge casing", () => {
  it("sentence-cases a lowercase enum value in the DOM, not just visually", () => {
    render(<Badge>active</Badge>);
    // textContent, not a style assertion — this is the point of the change.
    expect(screen.getByText("Active").textContent).toBe("Active");
  });

  it("capitalises only the first word", () => {
    render(<Badge>awaiting grade</Badge>);
    expect(screen.getByText("Awaiting grade")).toBeTruthy();
  });

  it("leaves an already-capitalised label alone", () => {
    render(<Badge>Overdue</Badge>);
    expect(screen.getByText("Overdue")).toBeTruthy();
  });

  it("does not mangle codes and identifiers", () => {
    render(<Badge>FS-1</Badge>);
    expect(screen.getByText("FS-1")).toBeTruthy();
  });

  it("passes interpolated fragments through untouched", () => {
    const score = 8;
    render(<Badge>Graded {score}/10</Badge>);
    // children is an array here, so sentenceCase must not try to index into it.
    expect(screen.getByText(/Graded 8\/10/)).toBeTruthy();
  });

  it("survives empty children", () => {
    const { container } = render(<Badge>{""}</Badge>);
    expect(container.querySelector("span")?.textContent).toBe("");
  });
});
