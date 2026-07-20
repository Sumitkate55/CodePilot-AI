import { Outlet } from "react-router-dom";

import { Brand } from "@/components/layout/Brand";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export function AuthLayout() {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="flex flex-col p-6 sm:p-10">
        <div className="flex items-center justify-between">
          <Brand />
          <ThemeToggle />
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 items-center py-12">
          <Outlet />
        </div>
      </section>
      <aside className="hidden bg-slate-950 p-12 text-slate-50 lg:flex lg:flex-col lg:justify-end">
        <div className="max-w-lg">
          <p className="text-sm font-semibold text-blue-300">Repository intelligence, without the noise.</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">
            Understand every moving part of your software.
          </h1>
          <p className="mt-5 text-base leading-7 text-slate-300">
            CodePilot AI will connect repository analysis, architecture, and code quality into one focused workspace.
          </p>
        </div>
      </aside>
    </div>
  );
}
