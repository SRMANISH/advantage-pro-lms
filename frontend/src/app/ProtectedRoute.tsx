import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "../features/auth/auth";
import { slugForRole, type RoleDef } from "./roles";

interface ProtectedRouteProps {
  role: RoleDef;
  children: ReactNode;
}

export function ProtectedRoute({ role, children }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="p-10 text-sm text-muted">Loading…</div>;
  }
  if (!user) {
    return <Navigate to={`/login/${role.slug}`} replace />;
  }
  // Signed in, but viewing another role's portal — send them to their own.
  if (user.role !== role.value) {
    return <Navigate to={`/${slugForRole(user.role)}`} replace />;
  }
  return <>{children}</>;
}
