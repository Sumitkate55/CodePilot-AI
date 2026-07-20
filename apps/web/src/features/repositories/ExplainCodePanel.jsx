import { useState } from "react";
import { Braces, ChevronRight, CircleAlert, FileCode2, LoaderCircle, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const explanationSections = [
  ["Purpose", "purpose"],
  ["Inputs", "inputs"],
  ["Outputs", "outputs"],
  ["Dependencies", "dependencies"],
  ["Logic", "logic"],
  ["Limitations", "limitations"],
];

export function ExplainCodePanel({ repositoryId, functions, error, isLoading, explanationMutation }) {
  const [selectedFunction, setSelectedFunction] = useState(null);
  const [explanation, setExplanation] = useState(null);

  const handleFunctionClick = async (functionItem) => {
    setSelectedFunction(functionItem);
    setExplanation(null);
    const result = await explanationMutation.mutateAsync({
      repositoryId,
      path: functionItem.path,
      line: functionItem.line,
    });
    setExplanation(result);
  };

  if (isLoading) {
    return <div className="mt-8 h-80 animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (!functions) {
    const message = error?.status === 404
      ? "Analyze this repository to list functions available for explanation."
      : error?.message ?? "Code explanations are unavailable.";
    return (
      <Card className="mt-8 border-dashed">
        <CardHeader>
          <p className="text-sm font-medium text-primary">Explain code</p>
          <CardTitle className="mt-1">Understand a selected function</CardTitle>
          <CardDescription className="mt-1">{message}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="mt-8">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-primary">Explain code</p>
            <CardTitle className="mt-1">Understand a function</CardTitle>
            <CardDescription className="mt-1">Select a detected function. Explanations are grounded only in its source excerpt.</CardDescription>
          </div>
          {explanation ? <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">{explanation.model}</span> : null}
        </div>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <FunctionList
          functions={functions}
          selectedFunction={selectedFunction}
          isExplaining={explanationMutation.isPending}
          onSelect={handleFunctionClick}
        />
        <ExplanationResult
          selectedFunction={selectedFunction}
          explanation={explanation}
          error={explanationMutation.error}
          isExplaining={explanationMutation.isPending}
        />
      </CardContent>
    </Card>
  );
}

function FunctionList({ functions, selectedFunction, isExplaining, onSelect }) {
  if (functions.length === 0) {
    return <p className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">No supported function declarations were detected in this repository.</p>;
  }
  return (
    <div className="max-h-112 space-y-2 overflow-auto pr-1">
      {functions.map((functionItem) => {
        const selected = selectedFunction?.path === functionItem.path && selectedFunction?.line === functionItem.line;
        return (
          <Button
            key={`${functionItem.path}:${functionItem.line}`}
            variant={selected ? "secondary" : "outline"}
            className="h-auto w-full justify-start gap-3 px-3 py-3 text-left"
            type="button"
            disabled={isExplaining}
            onClick={() => onSelect(functionItem)}
          >
            {selected && isExplaining ? <LoaderCircle className="size-4 shrink-0 animate-spin" aria-hidden="true" /> : <Braces className="size-4 shrink-0 text-primary" aria-hidden="true" />}
            <span className="min-w-0 flex-1"><span className="block truncate font-medium">{functionItem.name}</span><span className="mt-1 block truncate text-xs text-muted-foreground">{functionItem.path} · line {functionItem.line}</span></span>
            <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          </Button>
        );
      })}
    </div>
  );
}

function ExplanationResult({ selectedFunction, explanation, error, isExplaining }) {
  if (isExplaining) {
    return <div className="grid min-h-64 place-items-center rounded-xl border border-dashed border-border bg-muted/20 p-6 text-center"><div><LoaderCircle className="mx-auto size-6 animate-spin text-primary" aria-hidden="true" /><p className="mt-3 text-sm font-medium">Explaining {selectedFunction?.name}</p><p className="mt-1 text-sm text-muted-foreground">Reading only the selected function source.</p></div></div>;
  }
  if (error) {
    return <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-700"><p className="flex items-center gap-2 font-medium"><CircleAlert className="size-4" aria-hidden="true" />Explanation unavailable</p><p className="mt-2">{error.message}</p></div>;
  }
  if (!explanation) {
    return <div className="grid min-h-64 place-items-center rounded-xl border border-dashed border-border bg-muted/20 p-6 text-center"><div><Sparkles className="mx-auto size-6 text-primary" aria-hidden="true" /><p className="mt-3 text-sm font-medium">Select a function to explain it</p><p className="mt-1 text-sm text-muted-foreground">Purpose, inputs, outputs, dependencies, and logic will appear here.</p></div></div>;
  }
  const content = explanation.content ?? {};
  return (
    <div className="space-y-4 rounded-xl border border-border p-5">
      <p className="flex items-center gap-2 text-sm font-semibold"><FileCode2 className="size-4 text-primary" aria-hidden="true" />{explanation.function.path} · lines {explanation.function.line}–{explanation.end_line}</p>
      <div className="grid gap-4 sm:grid-cols-2">{explanationSections.map(([title, key]) => <ExplanationSection key={key} title={title} value={content[key]} />)}</div>
    </div>
  );
}

function ExplanationSection({ title, value }) {
  const items = Array.isArray(value) ? value : [];
  const text = typeof value === "string" ? value : null;
  if (!text && items.length === 0) {
    return null;
  }
  return <div><h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>{text ? <p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p> : <ul className="mt-2 space-y-1.5 text-sm leading-6 text-muted-foreground">{items.map((item) => <li key={item}>• {item}</li>)}</ul>}</div>;
}
