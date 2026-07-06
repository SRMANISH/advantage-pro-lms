import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { ProtectedRoute } from "./ProtectedRoute";
import { ROLES } from "./roles";

const student = ROLES.find((r) => r.value === "student")!;

const mockUseAuth = vi.fn();
vi.mock("../features/auth/auth", () => ({
  useAuth: () => mockUseAuth(),
}));

// The guard is mounted at a path distinct from either role's own dashboard, so the
// redirect-destination routes below never collide with the route under test.
function renderGuard(role = student) {
  return render(
    <MemoryRouter initialEntries={["/protected"]}>
      <Routes>
        <Route path={`/login/${role.slug}`} element={<div>login page</div>} />
        <Route path="/faculty" element={<div>faculty dashboard</div>} />
        <Route path="/student" element={<div>student dashboard</div>} />
        <Route
          path="/protected"
          element={
            <ProtectedRoute role={role}>
              <div>protected content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("shows a spinner while auth is loading", () => {
    mockUseAuth.mockReturnValue({ user: null, isLoading: true });
    renderGuard();
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
    expect(screen.queryByText("login page")).not.toBeInTheDocument();
  });

  it("redirects to the role's login page when signed out", () => {
    mockUseAuth.mockReturnValue({ user: null, isLoading: false });
    renderGuard();
    expect(screen.getByText("login page")).toBeInTheDocument();
  });

  it("renders the protected content when the user matches the route's role", () => {
    mockUseAuth.mockReturnValue({ user: { role: "student" }, isLoading: false });
    renderGuard(student);
    expect(screen.getByText("protected content")).toBeInTheDocument();
  });

  it("redirects a signed-in user of a different role to their own portal", () => {
    mockUseAuth.mockReturnValue({ user: { role: "faculty" }, isLoading: false });
    renderGuard(student); // route is /student, but the signed-in user is faculty
    expect(screen.getByText("faculty dashboard")).toBeInTheDocument();
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });
});
