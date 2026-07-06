import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";

import { FileUpload } from "./FileUpload";

function Controlled() {
  const [file, setFile] = useState<File | null>(null);
  return <FileUpload file={file} onFile={setFile} hint="PDF up to 25 MB" />;
}

describe("FileUpload", () => {
  it("shows the drop-zone prompt and hint when empty", () => {
    render(<Controlled />);
    expect(screen.getByText(/drag a file here/i)).toBeInTheDocument();
    expect(screen.getByText("PDF up to 25 MB")).toBeInTheDocument();
  });

  it("selecting a file via the hidden input shows the file chip", () => {
    render(<Controlled />);
    const file = new File(["hello"], "notes.pdf", { type: "application/pdf" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText("notes.pdf")).toBeInTheDocument();
  });

  it("dropping a file selects it", () => {
    render(<Controlled />);
    const file = new File(["hello"], "dropped.png", { type: "image/png" });
    const dropzone = screen.getByRole("button");
    fireEvent.drop(dropzone, { dataTransfer: { files: [file] } });
    expect(screen.getByText("dropped.png")).toBeInTheDocument();
  });

  it("Remove clears the selection back to the empty prompt", () => {
    render(<Controlled />);
    const file = new File(["hello"], "notes.pdf", { type: "application/pdf" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /remove/i }));
    expect(screen.queryByText("notes.pdf")).not.toBeInTheDocument();
    expect(screen.getByText(/drag a file here/i)).toBeInTheDocument();
  });

  it("Enter on the focused drop-zone opens the file picker", () => {
    render(<Controlled />);
    const dropzone = screen.getByRole("button");
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const clickSpy = vi.spyOn(input, "click");
    fireEvent.keyDown(dropzone, { key: "Enter" });
    expect(clickSpy).toHaveBeenCalled();
  });
});
