import { AlertCircle, Home } from "lucide-react";
import { Link, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function RouteErrorPage() {
  const error = useRouteError();
  const message = error instanceof Error ? error.message : "The requested route could not be loaded.";

  return (
    <main className="grid min-h-screen place-items-center p-6 text-center">
      <section className="max-w-md">
        <AlertCircle className="mx-auto size-10 text-amber-500" aria-hidden="true" />
        <h1 className="mt-5 text-3xl font-semibold tracking-tight">Unable to load this page</h1>
        <p className="mt-3 text-muted-foreground">{message}</p>
        <Button asChild className="mt-7">
          <Link to="/welcome">
            <Home className="size-4" aria-hidden="true" />
            Return home
          </Link>
        </Button>
      </section>
    </main>
  );
}
