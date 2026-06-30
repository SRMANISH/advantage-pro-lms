import { Component, type ReactNode } from "react";

import { Button } from "../design-system";

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
}

/** Catches render errors so one broken screen never blanks the whole app. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    // eslint-disable-next-line no-console
    console.error("Unhandled UI error:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-appbg p-6 text-center">
          <h1 className="text-lg font-semibold text-ink">Something went wrong</h1>
          <p className="mt-1 max-w-sm text-sm text-muted">
            An unexpected error occurred. Reloading the page usually fixes it.
          </p>
          <Button className="mt-4" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
