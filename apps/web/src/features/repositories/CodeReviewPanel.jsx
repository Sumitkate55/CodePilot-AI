import { useMemo, useState } from "react";
import { FileCode2, Filter, LoaderCircle, ShieldCheck, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/features/repositories/formatters";

const severities = ["critical", "high", "medium", "low"];
const categoryLabels = {
  security: "Security",
  performance: "Performance",
  naming: "Naming",
  dead_code: "Dead code",
  code_smell: "Code smell",
  long_function: "Long function",
  duplicate_code: "Duplicate code",
};

export function CodeReviewPanel({ review, error, isLoading, reviewMutation, onReview }) {
  const [severityFilter, setSeverityFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const findings = useMemo(() => (review?.findings ?? []).filter((finding) => (
    (severityFilter === "all" || finding.severity === severityFilter)
    && (categoryFilter === "all" || finding.category === categoryFilter)
  )), [review?.findings, severityFilter, categoryFilter]);

  if (isLoading) {
    return <div className="mt-8 h-96 animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (!review) {
    const message = error?.status === 404
      ? "Analyze this repository, then run a source-grounded review of its latest version."
      : error?.message ?? "Repository code review is unavailable.";
    return (
      <Card className="mt-8 border-dashed">
        <CardHeader>
          <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><ShieldCheck className="size-5" aria-hidden="true" /></span>
          <CardTitle className="mt-3">Repository code review</CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" disabled={reviewMutation.isPending} onClick={onReview}>
            {reviewMutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Sparkles className="size-4" aria-hidden="true" />}
            {reviewMutation.isPending ? "Reviewing repository" : "Run code review"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const counts = review.severity_counts ?? {};
  return (
    <Card className="mt-8">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-primary">Repository code review</p>
            <CardTitle className="mt-1">Quality findings</CardTitle>
            <CardDescription className="mt-1">Reviewed {review.scanned_file_count.toLocaleString()} safe source files on {formatDate(review.updated_at)}.</CardDescription>
          </div>
          <Button variant="outline" type="button" disabled={reviewMutation.isPending} onClick={onReview}>
            {reviewMutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <ShieldCheck className="size-4" aria-hidden="true" />}
            {reviewMutation.isPending ? "Reviewing" : "Run again"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {severities.map((severity) => <SeverityStat key={severity} severity={severity} value={counts[severity] ?? 0} />)}
        </div>
        <ReviewFilters
          severity={severityFilter}
          category={categoryFilter}
          categories={review.category_counts ?? {}}
          onSeverity={setSeverityFilter}
          onCategory={setCategoryFilter}
        />
        {findings.length === 0 ? <EmptyReview /> : <div className="space-y-3">{findings.map((finding) => <ReviewFinding key={finding.key} finding={finding} />)}</div>}
      </CardContent>
    </Card>
  );
}

function SeverityStat({ severity, value }) {
  return <div className={`rounded-lg border p-4 ${severityTone(severity)}`}><p className="text-xs font-semibold uppercase tracking-wide">{severity}</p><p className="mt-1 text-2xl font-semibold">{Number(value).toLocaleString()}</p></div>;
}

function ReviewFilters({ severity, category, categories, onSeverity, onCategory }) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/20 p-3">
      <Filter className="size-4 text-muted-foreground" aria-hidden="true" />
      <select className="h-9 rounded-md border border-input bg-background px-3 text-sm" value={severity} onChange={(event) => onSeverity(event.target.value)} aria-label="Filter findings by severity">
        <option value="all">All severities</option>
        {severities.map((value) => <option key={value} value={value}>{capitalize(value)}</option>)}
      </select>
      <select className="h-9 rounded-md border border-input bg-background px-3 text-sm" value={category} onChange={(event) => onCategory(event.target.value)} aria-label="Filter findings by category">
        <option value="all">All categories</option>
        {Object.entries(categories).filter(([, count]) => count > 0).map(([value]) => <option key={value} value={value}>{categoryLabels[value] ?? value}</option>)}
      </select>
    </div>
  );
}

function ReviewFinding({ finding }) {
  return (
    <article className="rounded-xl border border-border bg-muted/10 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2"><span className={`rounded-full border px-2 py-0.5 text-xs font-semibold uppercase ${severityTone(finding.severity)}`}>{finding.severity}</span><span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">{categoryLabels[finding.category] ?? finding.category}</span></div>
          <h3 className="mt-3 font-semibold">{finding.title}</h3>
        </div>
        <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">{finding.confidence}% confidence</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{finding.description}</p>
      <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
        <p className="flex min-w-0 items-center gap-2 text-xs font-medium text-muted-foreground"><FileCode2 className="size-3.5 shrink-0 text-primary" aria-hidden="true" /><span className="truncate">{finding.path} · lines {finding.start_line}–{finding.end_line}</span></p>
        <p className="text-sm"><span className="font-semibold">Recommendation:</span> <span className="text-muted-foreground">{finding.recommendation}</span></p>
      </div>
    </article>
  );
}

function EmptyReview() {
  return <div className="grid min-h-40 place-items-center rounded-xl border border-dashed border-border bg-muted/20 p-6 text-center"><div><ShieldCheck className="mx-auto size-6 text-emerald-600" aria-hidden="true" /><p className="mt-3 font-medium">No findings match these filters</p><p className="mt-1 text-sm text-muted-foreground">Try a broader filter, or this reviewed source version has no detected issues.</p></div></div>;
}

function severityTone(severity) {
  const tones = {
    critical: "border-red-500/40 bg-red-500/10 text-red-700",
    high: "border-orange-500/40 bg-orange-500/10 text-orange-700",
    medium: "border-amber-500/40 bg-amber-500/10 text-amber-700",
    low: "border-sky-500/40 bg-sky-500/10 text-sky-700",
  };
  return tones[severity] ?? "border-border bg-muted text-muted-foreground";
}

function capitalize(value) {
  return `${value.slice(0, 1).toUpperCase()}${value.slice(1)}`;
}
