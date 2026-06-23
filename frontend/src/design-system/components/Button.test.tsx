import { render, screen } from "@testing-library/react";

import { Button } from "./Button";

describe("Button", () => {
  it("renders its label", () => {
    render(<Button>Sign in</Button>);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("applies the soft variant styles", () => {
    render(<Button variant="soft">Soft</Button>);
    expect(screen.getByRole("button", { name: "Soft" })).toHaveClass("bg-sky");
  });
});
