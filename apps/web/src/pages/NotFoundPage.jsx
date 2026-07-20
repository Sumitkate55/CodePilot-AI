import { Home, MapPinned } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center p-6 text-center">
      <section className="max-w-md">
        <MapPinned className="mx-auto size-10 text-primary" aria-hidden="true" />
        <p className="mt-5 text-sm font-medium text-primary">404</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">This route does not exist</h1>
        <p className="mt-3 text-muted-foreground">The page may have moved or the address may be incorrect.</p>
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
