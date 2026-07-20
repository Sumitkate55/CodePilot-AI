import { useEffect, useMemo, useState } from "react";
import {
  Beaker,
  CheckCircle2,
  CircleAlert,
  CodeXml,
  FileCode2,
  LoaderCircle,
  PanelLeft,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const coverageKinds = ["happy_path", "edge_cases", "invalid_inputs", "boundary_tests"];

export function TestGeneratorPanel({ dashboard, error, isLoading, generationMutation, onGenerate }) {
  const [selectedTargetKey, setSelectedTargetKey] = useState(null);
  const targets = useMemo(() => dashboard?.targets ?? [], [dashboard?.targets]);
  const generatedByTarget = useMemo(() => Object.fromEntries(
    (dashboard?.generated_tests ?? []).map((generatedTest) => [targetKey(generatedTest), generatedTest]),
  ), [dashboard?.generated_tests]);

  useEffect(() => {
    if (!selectedTargetKey && targets.length > 0) {
      setSelectedTargetKey(targetKey(targets[0]));
    }
  }, [selectedTargetKey, targets]);

  if (isLoading) {
    return <div className="mt-8 h-[35rem] animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (!dashboard) {
    const message = error?.status === 404
      ? "Analyze this repository first. CodePilot creates tests only for detected Python, JavaScript, TypeScript, and Java functions."
      : error?.message ?? "The unit-test generator is unavailable.";
    return (
      <Card className="mt-8 border-dashed">
        <CardHeader>
          <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><Beaker className="size-5" aria-hidden="true" /></span>
          <CardTitle className="mt-3">AI Test Generator</CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const selectedTarget = targets.find((target) => targetKey(target) === selectedTargetKey) ?? targets[0];
  const generatedTest = selectedTarget ? generatedByTarget[targetKey(selectedTarget)] : null;
  return (
    <Card className="mt-8 overflow-hidden">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-primary">AI Test Generator</p>
            <CardTitle className="mt-1">Create complete, framework-matched unit tests</CardTitle>
            <CardDescription className="mt-1">Tests are generated from the selected stored function only and cover happy, edge, invalid, and boundary scenarios.</CardDescription>
          </div>
          <div className="rounded-xl border border-primary/30 bg-primary/10 px-4 py-3 text-right"><p className="text-xs font-semibold uppercase tracking-wide text-primary">Supported targets</p><p className="mt-1 text-2xl font-semibold">{targets.length}</p><p className="mt-1 text-xs text-muted-foreground">pytest · Jest · JUnit</p></div>
        </div>
      </CardHeader>
      <CardContent>
        {targets.length === 0 ? <NoTargets /> : (
          <div className="grid overflow-hidden rounded-xl border border-border lg:grid-cols-[minmax(15rem,0.76fr)_minmax(0,1.7fr)]">
            <TargetSidebar
              generatedByTarget={generatedByTarget}
              selectedTargetKey={targetKey(selectedTarget)}
              targets={targets}
              onSelect={setSelectedTargetKey}
            />
            <TestWorkspace
              generatedTest={generatedTest}
              generationMutation={generationMutation}
              target={selectedTarget}
              onGenerate={onGenerate}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TargetSidebar({ generatedByTarget, selectedTargetKey, targets, onSelect }) {
  return (
    <aside className="border-b border-border bg-muted/15 lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3"><PanelLeft className="size-4 text-primary" aria-hidden="true" /><p className="text-sm font-semibold">Testable functions</p></div>
      <div className="max-h-[35rem] overflow-auto p-2">
        {targets.map((target) => {
          const selected = targetKey(target) === selectedTargetKey;
          const generated = generatedByTarget[targetKey(target)];
          return (
            <button
              key={targetKey(target)}
              type="button"
              onClick={() => onSelect(targetKey(target))}
              className={`mb-1.5 w-full rounded-lg border p-3 text-left transition-colors ${selected ? "border-primary bg-primary/10" : "border-transparent hover:border-border hover:bg-muted/40"}`}
            >
              <div className="flex items-center justify-between gap-2"><span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold uppercase text-muted-foreground">{target.framework}</span>{generated ? <CheckCircle2 className="size-4 text-emerald-600" aria-label="Test generated" /> : null}</div>
              <p className="mt-2 truncate text-sm font-medium">{target.function.name}</p>
              <p className="mt-1 truncate text-xs text-muted-foreground">{target.function.path} · line {target.function.line}</p>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

function TestWorkspace({ generatedTest, generationMutation, target, onGenerate }) {
  return (
    <div className="min-w-0 space-y-5 p-4 sm:p-5">
      <div>
        <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">{target.framework}</span><span className="text-xs text-muted-foreground">{target.function.path} · line {target.function.line}</span></div>
        <h3 className="mt-2 text-lg font-semibold">{target.function.name}</h3>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">Generate a full test file for this detected function. The generated artifact is saved against this immutable repository version.</p>
      </div>
      {generatedTest ? <GeneratedTestResult generatedTest={generatedTest} generationMutation={generationMutation} target={target} onGenerate={onGenerate} /> : <GenerateTests generationMutation={generationMutation} target={target} onGenerate={onGenerate} />}
    </div>
  );
}

function GenerateTests({ generationMutation, target, onGenerate }) {
  return (
    <div className="rounded-xl border border-dashed border-primary/40 bg-primary/5 p-5">
      <p className="font-semibold">Generate unit tests</p>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">CodePilot will produce a complete {target.framework} test file with all four required coverage scenarios. It does not write into your stored repository.</p>
      <GenerationError error={generationMutation.error} />
      <Button className="mt-4" type="button" disabled={generationMutation.isPending} onClick={() => onGenerate(target)}>
        {generationMutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Sparkles className="size-4" aria-hidden="true" />}
        {generationMutation.isPending ? "Generating tests" : "Generate test file"}
      </Button>
    </div>
  );
}

function GeneratedTestResult({ generatedTest, generationMutation, target, onGenerate }) {
  return (
    <section className="space-y-4 rounded-xl border border-border p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-600" aria-hidden="true" /><span className="text-sm font-medium">Generated test file</span></div><p className="mt-1 text-xs text-muted-foreground">{generatedTest.test_path}</p></div><span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">{generatedTest.model}</span></div>
      <p className="text-sm leading-6 text-muted-foreground">{generatedTest.summary}</p>
      <CoverageChecklist coverage={generatedTest.coverage} />
      <div className="overflow-hidden rounded-xl border border-border bg-slate-950 text-slate-100"><p className="flex items-center gap-2 border-b border-slate-700 px-4 py-3 text-sm font-semibold text-slate-100"><CodeXml className="size-4 text-blue-300" aria-hidden="true" />Complete {target.framework} suite</p><pre className="max-h-112 overflow-auto p-4 text-xs leading-5"><code>{generatedTest.test_code.split("\n").map((line, index) => <span key={`${index}:${line}`} className="block whitespace-pre text-slate-300">{line || " "}</span>)}</code></pre></div>
      {generatedTest.notes?.length ? <div><h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Notes</h4><ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">{generatedTest.notes.map((note) => <li key={note}>• {note}</li>)}</ul></div> : null}
      <GenerationError error={generationMutation.error} />
      <Button variant="outline" type="button" disabled={generationMutation.isPending} onClick={() => onGenerate(target)}>
        {generationMutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Sparkles className="size-4" aria-hidden="true" />}
        {generationMutation.isPending ? "Regenerating" : "Regenerate test file"}
      </Button>
    </section>
  );
}

function CoverageChecklist({ coverage }) {
  const available = new Set(coverage ?? []);
  return <div className="grid gap-2 sm:grid-cols-2">{coverageKinds.map((kind) => <div key={kind} className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${available.has(kind) ? "border-emerald-500/30 bg-emerald-500/10" : "border-border bg-muted/20"}`}><CheckCircle2 className={`size-4 ${available.has(kind) ? "text-emerald-600" : "text-muted-foreground"}`} aria-hidden="true" />{coverageLabel(kind)}</div>)}</div>;
}

function GenerationError({ error }) {
  return error ? <p className="mt-3 flex items-center gap-2 text-sm text-red-700"><CircleAlert className="size-4" aria-hidden="true" />{error.message}</p> : null;
}

function NoTargets() {
  return <div className="grid min-h-64 place-items-center rounded-xl border border-dashed border-border p-6 text-center"><div><FileCode2 className="mx-auto size-7 text-muted-foreground" aria-hidden="true" /><p className="mt-3 font-medium">No supported functions were detected</p><p className="mt-1 text-sm text-muted-foreground">Refresh repository intelligence after importing Python, JavaScript, TypeScript, or Java source files.</p></div></div>;
}

function targetKey(target) {
  return `${target.function.path}:${target.function.line}:${target.framework}`;
}

function coverageLabel(kind) {
  return kind.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
