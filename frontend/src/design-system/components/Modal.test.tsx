import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { Modal } from "./Modal";
import { QueryError } from "./QueryError";

/**
 * The dialog already declared role="dialog" and aria-modal="true" — a promise that focus is
 * managed and the rest of the page is inert. None of it was implemented, which is worse than
 * not declaring it: a screen-reader user is told they are in a modal, then Tab walks them out
 * into the page behind it.
 */
describe("Modal accessibility", () => {
  const Fixture = ({ onClose = () => {} }: { onClose?: () => void }) => (
    <Modal open onClose={onClose} title="Confirm">
      <button>First</button>
      <button>Second</button>
    </Modal>
  );

  it("moves focus into the dialog when it opens", async () => {
    render(<Fixture />);
    await vi.waitFor(() => expect(document.activeElement).toBe(screen.getByText("First")));
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(<Fixture onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  // Both wrap tests wait for the mount-time focus to land first. The component focuses the
  // first control on a requestAnimationFrame, so dispatching a key before that resolves races
  // it — and the forward case then passes for the wrong reason, since the rAF happens to
  // leave focus exactly where the assertion expects it.
  it("wraps Tab from the last control back to the first", async () => {
    render(<Fixture />);
    const first = screen.getByText("First");
    const last = screen.getByText("Second");
    await vi.waitFor(() => expect(document.activeElement).toBe(first));
    last.focus();

    fireEvent.keyDown(document, { key: "Tab" });

    expect(document.activeElement).toBe(first);
  });

  it("wraps Shift+Tab from the first control back to the last", async () => {
    render(<Fixture />);
    const first = screen.getByText("First");
    const last = screen.getByText("Second");
    await vi.waitFor(() => expect(document.activeElement).toBe(first));

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });

    expect(document.activeElement).toBe(last);
  });

  it("returns focus to whatever opened it", async () => {
    const Host = () => {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Opener</button>
          <Modal open={open} onClose={() => setOpen(false)} title="T">
            <button>Inside</button>
          </Modal>
        </>
      );
    };
    render(<Host />);
    const opener = screen.getByText("Opener");
    opener.focus();
    fireEvent.click(opener);
    await vi.waitFor(() => expect(document.activeElement).toBe(screen.getByText("Inside")));

    fireEvent.keyDown(document, { key: "Escape" });

    // Without this the keyboard user is dropped onto <body>, at the top of the document.
    await vi.waitFor(() => expect(document.activeElement).toBe(opener));
  });
});

describe("QueryError", () => {
  it("announces itself and offers a retry", () => {
    const onRetry = vi.fn();
    render(<QueryError onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.click(screen.getByText("Try again"));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("omits the retry control when there is nothing to retry", () => {
    render(<QueryError />);
    expect(screen.queryByText("Try again")).toBeNull();
  });
});
