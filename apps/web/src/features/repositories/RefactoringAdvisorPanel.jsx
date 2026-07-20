import { useEffect, useMemo, useState } from "react";
import {
  Check,
  ChevronRight,
  CircleAlert,
  CodeXml,
  GitCompareArrows,
  LoaderCircle,
  PanelLeft,
  Sparkles,
  ThumbsDown,
  WandSparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useRepositorySourceFile } from "@/features/repositories/repository-queries";

const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };

export function RefactoringAdvisorPanel({
  repositoryId,
  dashboard,
  error,
  isLoading,
  proposalMutation,
  decisionMutation,
  onGenerate,
  onDecision,
}) {
  const [selectedFindingKey, setSelectedFindingKey] = useState(null);
  const findings = useMemo(() => [...(dashboard?.review?.findings ?? [])].sort((left, right) => (
    severityOrder[left.severity] - severityOrder[right.severity]
  )), [dashboard?.review?.findings]);
  const proposalByFinding = useMemo(() => Object.fromEntries(
    (dashboard?.proposals ?? []).map((proposal) => [proposal.finding_key, proposal]),
  ), [dashboard?.proposals]);

  useEffect(() => {
    if (!selectedFindingKey && findings.length > 0) {
      setSelectedFindingKey(findings[0].key);
    }
  }, [findings, selectedFindingKey]);

  if (isLoading) {
    return <div className="mt-8 h-[42rem] animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (!dashboard) {
    const message = error?.status === 404
      ? "Run repository code review first. The advisor turns each review finding into a source-grounded proposal."
      : error?.message ?? "The refactoring advisor is unavailable.";
    return (
      <Card className="mt-8 border-dashed">
        <CardHeader>
          <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><WandSparkles className="size-5" aria-hidden="true" /></span>
          <CardTitle className="mt-3">AI Refactoring Advisor</CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const selectedFinding = findings.find((finding) => finding.key === selectedFindingKey) ?? findings[0];
  const selectedProposal = selectedFinding ? proposalByFinding[selectedFinding.key] : null;
  return (
    <Card className="mt-8 overflow-hidden">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-primary">AI Refactoring Advisor</p>
            <CardTitle className="mt-1">Turn findings into safe, reviewable changes</CardTitle>
            <CardDescription className="mt-1">Proposals use only selected repository source. Accepting records a decision; your stored source remains immutable.</CardDescription>
          </div>
          <ScoreBadge score={dashboard.score} />
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <ImpactReport score={dashboard.score} />
        {findings.length === 0 ? <NoFindings /> : (
          <div className="grid overflow-hidden rounded-xl border border-border lg:grid-cols-[minmax(15rem,0.76fr)_minmax(0,1.7fr)]">
            <FindingSidebar
              findings={findings}
              proposalByFinding={proposalByFinding}
              selectedFindingKey={selectedFinding?.key}
              onSelect={setSelectedFindingKey}
            />
            <AdvisorWorkspace
              repositoryId={repositoryId}
              finding={selectedFinding}
              proposal={selectedProposal}
              proposalMutation={proposalMutation}
              decisionMutation={decisionMutation}
              onGenerate={onGenerate}
              onDecision={onDecision}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ScoreBadge({ score }) {
  return <div className="rounded-xl border border-primary/30 bg-primary/10 px-4 py-3 text-right"><p className="text-xs font-semibold uppercase tracking-wide text-primary">Live repository score</p><p className="mt-1 text-3xl font-semibold">{score.current}<span className="text-base text-muted-foreground">/100</span></p><p className="mt-1 text-xs text-muted-foreground">Potential: {score.potential}/100</p></div>;
}

function ImpactReport({ score }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <ImpactMetric label="Accepted" value={score.accepted_count} detail={`+${score.accepted_quality_gain} score`} tone="emerald" />
      <ImpactMetric label="Ready to decide" value={score.proposed_count} detail={`+${score.available_quality_gain} potential`} tone="primary" />
      <ImpactMetric label="Rejected" value={score.rejected_count} detail="kept for audit" tone="muted" />
      <ImpactMetric label="Remaining findings" value={score.remaining_finding_count} detail="in latest review" tone="amber" />
    </div>
  );
}

function ImpactMetric({ label, value, detail, tone }) {
  const tones = {
    emerald: "border-emerald-500/30 bg-emerald-500/10",
    primary: "border-primary/30 bg-primary/10",
    muted: "border-border bg-muted/30",
    amber: "border-amber-500/30 bg-amber-500/10",
  };
  return <div className={`rounded-lg border p-3 ${tones[tone]}`}><p className="text-xs font-medium text-muted-foreground">{label}</p><p className="mt-1 text-xl font-semibold">{Number(value).toLocaleString()}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>;
}

function FindingSidebar({ findings, proposalByFinding, selectedFindingKey, onSelect }) {
  return (
    <aside className="border-b border-border bg-muted/15 lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3"><PanelLeft className="size-4 text-primary" aria-hidden="true" /><p className="text-sm font-semibold">Review findings</p></div>
      <div className="max-h-[39rem] overflow-auto p-2">
        {findings.map((finding) => {
          const proposal = proposalByFinding[finding.key];
          const selected = finding.key === selectedFindingKey;
          return (
            <button
              key={finding.key}
              type="button"
              onClick={() => onSelect(finding.key)}
              className={`mb-1.5 w-full rounded-lg border p-3 text-left transition-colors ${selected ? "border-primary bg-primary/10" : "border-transparent hover:border-border hover:bg-muted/40"}`}
            >
              <div className="flex items-start justify-between gap-2"><span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${severityTone(finding.severity)}`}>{finding.severity}</span>{proposal ? <ProposalStatus status={proposal.status} /> : null}</div>
              <p className="mt-2 line-clamp-2 text-sm font-medium">{finding.title}</p>
              <p className="mt-1 truncate text-xs text-muted-foreground">{finding.path} · line {finding.start_line}</p>
              <ChevronRight className="ml-auto mt-2 size-4 text-muted-foreground" aria-hidden="true" />
            </button>
          );
        })}
      </div>
    </aside>
  );
}

function AdvisorWorkspace({ repositoryId, finding, proposal, proposalMutation, decisionMutation, onGenerate, onDecision }) {
  const { data: sourceFile, error: sourceError, isLoading: isSourceLoading } = useRepositorySourceFile(repositoryId, finding?.path);
  if (!finding) {
    return <div className="grid min-h-96 place-items-center p-6 text-center text-sm text-muted-foreground">Select a review finding to begin.</div>;
  }
  return (
    <div className="min-w-0 space-y-5 p-4 sm:p-5">
      <div>
        <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">{finding.category.replace("_", " ")}</span><span className="text-xs text-muted-foreground">{finding.confidence}% review confidence</span></div>
        <h3 className="mt-2 text-lg font-semibold">{finding.title}</h3>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{finding.recommendation}</p>
      </div>
      <HighlightedSource finding={finding} sourceFile={sourceFile} error={sourceError} isLoading={isSourceLoading} />
      {proposal ? <ProposalResult proposal={proposal} decisionMutation={decisionMutation} onDecision={onDecision} /> : <GenerateProposal finding={finding} mutation={proposalMutation} onGenerate={onGenerate} />}
    </div>
  );
}

function HighlightedSource({ finding, sourceFile, error, isLoading }) {
  if (isLoading) {
    return <div className="h-48 animate-pulse rounded-xl border border-border bg-muted/30" />;
  }
  if (error) {
    return <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-700">{error.message}</div>;
  }
  if (!sourceFile) {
    return null;
  }
  const firstLine = Math.max(1, finding.start_line - 6);
  const lastLine = Math.min(sourceFile.content.split("\n").length, finding.end_line + 6);
  const lines = sourceFile.content.split("\n").slice(firstLine - 1, lastLine);
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-slate-950 text-slate-100">
      <p className="flex items-center gap-2 border-b border-slate-700 px-4 py-3 text-xs font-medium text-slate-300"><CodeXml className="size-4 text-blue-300" aria-hidden="true" />{finding.path} · highlighted review location</p>
      <pre className="max-h-80 overflow-auto p-3 text-xs leading-5"><code>{lines.map((line, index) => {
        const lineNumber = firstLine + index;
        const highlighted = lineNumber >= finding.start_line && lineNumber <= finding.end_line;
        return <span key={lineNumber} className={`grid grid-cols-[3rem_minmax(0,1fr)] px-2 ${highlighted ? "bg-amber-400/20 text-white" : "text-slate-300"}`}><span className="select-none text-slate-500">{lineNumber}</span><span className="whitespace-pre-wrap break-words">{line || " "}</span></span>;
      })}</code></pre>
    </div>
  );
}

function GenerateProposal({ finding, mutation, onGenerate }) {
  return (
    <div className="rounded-xl border border-dashed border-primary/40 bg-primary/5 p-5">
      <p className="font-semibold">Generate a refactor proposal</p>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">CodePilot will create a complete replacement for the displayed source context and a Git-style diff. It will not change your stored repository.</p>
      {mutation.error ? <p className="mt-3 flex items-center gap-2 text-sm text-red-700"><CircleAlert className="size-4" aria-hidden="true" />{mutation.error.message}</p> : null}
      <Button className="mt-4" type="button" disabled={mutation.isPending} onClick={() => onGenerate(finding.key)}>
        {mutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Sparkles className="size-4" aria-hidden="true" />}
        {mutation.isPending ? "Generating refactor" : "Generate refactor"}
      </Button>
    </div>
  );
}

function ProposalResult({ proposal, decisionMutation, onDecision }) {
  return (
    <section className="space-y-4 rounded-xl border border-border p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><ProposalStatus status={proposal.status} /><span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium capitalize">{proposal.risk} risk</span></div><h4 className="mt-2 font-semibold">{proposal.title}</h4></div><span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">{proposal.confidence}% confidence · +{proposal.estimated_quality_gain} potential</span></div>
      <p className="text-sm leading-6 text-muted-foreground">{proposal.rationale}</p>
      <DiffView diff={proposal.diff} />
      <div className="grid gap-4 md:grid-cols-2"><ProposalList title="Expected impact" items={proposal.impact_summary} /><ProposalList title="Suggested verification" items={proposal.testing_steps} /></div>
      <p className="text-xs text-muted-foreground">Proposal generated by {proposal.model}. Accepting records your decision and updates the projected score; copy the diff into your actual repository to apply it.</p>
      {proposal.status === "proposed" ? <div className="flex flex-wrap gap-2"><Button type="button" disabled={decisionMutation.isPending} onClick={() => onDecision(proposal.id, "accepted")}><Check className="size-4" aria-hidden="true" />Accept proposal</Button><Button variant="outline" type="button" disabled={decisionMutation.isPending} onClick={() => onDecision(proposal.id, "rejected")}><ThumbsDown className="size-4" aria-hidden="true" />Reject</Button></div> : null}
      {decisionMutation.error ? <p className="flex items-center gap-2 text-sm text-red-700"><CircleAlert className="size-4" aria-hidden="true" />{decisionMutation.error.message}</p> : null}
    </section>
  );
}

function DiffView({ diff }) {
  return <div className="overflow-hidden rounded-xl border border-border bg-slate-950"><p className="flex items-center gap-2 border-b border-slate-700 px-4 py-3 text-sm font-semibold text-slate-100"><GitCompareArrows className="size-4 text-blue-300" aria-hidden="true" />Git diff</p><pre className="max-h-96 overflow-auto p-4 text-xs leading-5"><code>{diff.split("\n").map((line, index) => <span key={`${index}:${line}`} className={`block whitespace-pre ${diffTone(line)}`}>{line || " "}</span>)}</code></pre></div>;
}

function ProposalList({ title, items }) {
  if (!items?.length) {
    return null;
  }
  return <div><h5 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h5><ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">{items.map((item) => <li key={item}>• {item}</li>)}</ul></div>;
}

function ProposalStatus({ status }) {
  const labels = { proposed: "Proposed", accepted: "Accepted", rejected: "Rejected" };
  const tones = { proposed: "bg-primary/10 text-primary", accepted: "bg-emerald-500/10 text-emerald-700", rejected: "bg-muted text-muted-foreground" };
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${tones[status] ?? tones.proposed}`}>{labels[status] ?? status}</span>;
}

function NoFindings() {
  return <div className="grid min-h-64 place-items-center rounded-xl border border-dashed border-border p-6 text-center"><div><WandSparkles className="mx-auto size-7 text-emerald-600" aria-hidden="true" /><p className="mt-3 font-medium">No reviewed findings need refactoring</p><p className="mt-1 text-sm text-muted-foreground">Run code review again after source changes to scan the latest stored version.</p></div></div>;
}

function severityTone(severity) {
  const tones = { critical: "bg-red-500/15 text-red-700", high: "bg-orange-500/15 text-orange-700", medium: "bg-amber-500/15 text-amber-700", low: "bg-sky-500/15 text-sky-700" };
  return tones[severity] ?? "bg-muted text-muted-foreground";
}

function diffTone(line) {
  if (line.startsWith("+++")) return "text-slate-300";
  if (line.startsWith("---")) return "text-slate-300";
  if (line.startsWith("+")) return "bg-emerald-500/20 text-emerald-200";
  if (line.startsWith("-")) return "bg-red-500/20 text-red-200";
  if (line.startsWith("@@")) return "text-blue-300";
  return "text-slate-300";
}
