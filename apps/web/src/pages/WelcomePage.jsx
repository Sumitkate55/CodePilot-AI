import { Braces, ChartNoAxesCombined, MessageSquareText, Network } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

const capabilities = [
  {
    title: "Repository intelligence",
    description: "Map languages, frameworks, dependencies, and the structure behind the source.",
    Icon: Braces,
  },
  {
    title: "Architecture clarity",
    description: "Explore services and dependencies as a navigable system, not a folder tree.",
    Icon: Network,
  },
  {
    title: "Grounded answers",
    description: "Ask repository questions with source-aware context and clear evidence.",
    Icon: MessageSquareText,
  },
  {
    title: "Quality direction",
    description: "Prioritize meaningful fixes with review findings and refactoring impact.",
    Icon: ChartNoAxesCombined,
  },
];

export function WelcomePage() {
  return (
    <main>
      <section className="mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="mx-auto max-w-3xl text-center"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">Codebase intelligence</p>
          <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-6xl">
            See the system behind your source code.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            CodePilot AI turns a repository into a clear, searchable, actionable engineering workspace.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link to="/register">Create your workspace</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </motion.div>

        <div className="mt-20 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {capabilities.map(({ title, description, Icon }, index) => (
            <motion.article
              key={title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: index * 0.08 }}
              className="rounded-xl border border-border bg-card p-6 shadow-sm"
            >
              <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <h2 className="mt-5 font-semibold">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
            </motion.article>
          ))}
        </div>
      </section>
    </main>
  );
}
