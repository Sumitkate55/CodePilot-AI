import { Component } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

export class AppErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error("Uncaught application error", error);
  }

  handleReset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="grid min-h-screen place-items-center p-6">
        <section className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-sm">
          <AlertTriangle className="mx-auto mb-4 size-10 text-amber-500" aria-hidden="true" />
          <h1 className="text-xl font-semibold">Something went wrong</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            The workspace could not be displayed. You can safely try loading it again.
          </p>
          <Button className="mt-6" onClick={this.handleReset}>
            <RotateCcw className="size-4" aria-hidden="true" />
            Try again
          </Button>
        </section>
      </main>
    );
  }
}
