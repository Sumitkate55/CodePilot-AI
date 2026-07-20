import { AlertCircle, ArrowRight, BarChart3, Clock3, Database, FolderGit2, Plus, RefreshCw, Sparkles } from "lucide-react";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatBytes, formatDate } from "@/features/repositories/formatters";
import { useRepositories } from "@/features/repositories/repository-queries";

export function DashboardPage() {
  const { data: repositories = [], error, isLoading, refetch, isFetching } = useRepositories();
  const dashboard = useMemo(() => buildDashboard(repositories), [repositories]);

  return (
    <section className="mx-auto max-w-6xl">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Workspace</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Your repositories</h1>
          <p className="mt-2 text-muted-foreground">Import a codebase to begin building its intelligence profile.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" type="button" disabled={isFetching} onClick={() => refetch()}>
            <RefreshCw className={isFetching ? "size-4 animate-spin" : "size-4"} aria-hidden="true" />
            Refresh
          </Button>
          <Button asChild>
            <Link to="/repositories/new">
              <Plus className="size-4" aria-hidden="true" />
              Add repository
            </Link>
          </Button>
        </div>
      </div>

      {isLoading ? <RepositoryLoadingState /> : null}
      {error ? <RepositoryError error={error} onRetry={refetch} /> : null}
      {!isLoading && !error && repositories.length === 0 ? <RepositoryEmptyState /> : null}
      {!isLoading && !error && repositories.length > 0 ? (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric icon={FolderGit2} label="Repositories" value={dashboard.repositoryCount} detail={`${dashboard.githubCount} GitHub · ${dashboard.zipCount} ZIP`} />
            <Metric icon={Database} label="Stored files" value={dashboard.fileCount.toLocaleString()} detail={`${dashboard.versionCount} immutable versions`} />
            <Metric icon={BarChart3} label="Workspace size" value={formatBytes(dashboard.sizeBytes)} detail="Latest source versions" />
            <Metric icon={Sparkles} label="Readiness" value={`${dashboard.readiness}%`} detail="Import and version-history completeness" />
          </div>
          <div className="mt-8 grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
            <Card><CardHeader><CardTitle>Repository activity</CardTitle><CardDescription>Latest stored source versions, ordered by import time.</CardDescription></CardHeader><CardContent><ActivityChart items={dashboard.activity} /></CardContent></Card>
            <Card><CardHeader><CardTitle>Quick actions</CardTitle><CardDescription>Continue building repository intelligence.</CardDescription></CardHeader><CardContent className="space-y-3"><Button asChild className="w-full justify-between"><Link to="/repositories/new">Import repository <Plus className="size-4" /></Link></Button>{dashboard.latestRepository ? <Button asChild variant="outline" className="w-full justify-between"><Link to={`/repositories/${dashboard.latestRepository.id}`}>Open latest repository <ArrowRight className="size-4" /></Link></Button> : null}<p className="pt-2 text-xs leading-5 text-muted-foreground">Readiness reflects whether a repository has stored source and retained import history. Run analysis inside a repository for AI features.</p></CardContent></Card>
          </div>
          <Card className="mt-8"><CardHeader><CardTitle>Repository history</CardTitle><CardDescription>Every import is retained as an immutable source version.</CardDescription></CardHeader><CardContent><ol className="divide-y divide-border">{dashboard.history.map((item) => <li key={`${item.repository.id}:${item.version.id}`} className="flex flex-wrap items-center gap-3 py-3 text-sm"><Clock3 className="size-4 text-primary" /><span className="font-medium">{item.repository.name}</span><span className="text-muted-foreground">Version {item.version.version_number} · {item.version.file_count.toLocaleString()} files · {formatDate(item.version.created_at)}</span><Link className="ml-auto text-primary hover:underline" to={`/repositories/${item.repository.id}`}>Open</Link></li>)}</ol></CardContent></Card>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {repositories.map((repository) => {
            const latest = repository.versions[0];
            return (
              <Card key={repository.id} className="transition-shadow hover:shadow-md">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                      <FolderGit2 className="size-5" aria-hidden="true" />
                    </span>
                    <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                      {repository.source_type === "github" ? "GitHub" : "ZIP upload"}
                    </span>
                  </div>
                  <CardTitle className="mt-4 text-lg">{repository.name}</CardTitle>
                  <CardDescription>
                    {latest
                      ? `Version ${latest.version_number} · ${latest.file_count.toLocaleString()} files · ${formatBytes(latest.size_bytes)}`
                      : "No stored version"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between gap-4">
                  <p className="text-xs text-muted-foreground">
                    {latest ? `Imported ${formatDate(latest.created_at)}` : "Awaiting import"}
                  </p>
                  <Button asChild variant="ghost" size="sm">
                    <Link to={`/repositories/${repository.id}`}>
                      View
                      <ArrowRight className="size-3.5" aria-hidden="true" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
        </>
      ) : null}
    </section>
  );
}

function Metric({ icon: Icon, label, value, detail }) { return <Card><CardContent className="p-5"><div className="flex items-center justify-between"><p className="text-sm text-muted-foreground">{label}</p><Icon className="size-4 text-primary" /></div><p className="mt-2 text-2xl font-semibold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></CardContent></Card>; }

function ActivityChart({ items }) { const maximum = Math.max(...items.map((item) => item.version.file_count), 1); return <div className="flex h-48 items-end gap-3">{items.slice(0, 8).reverse().map((item) => <div key={item.version.id} className="flex min-w-0 flex-1 flex-col items-center gap-2"><span className="text-xs text-muted-foreground">{item.version.file_count}</span><div className="w-full rounded-t-md bg-primary/80" style={{ height: `${Math.max(12, (item.version.file_count / maximum) * 145)}px` }} title={`${item.repository.name}: ${item.version.file_count} files`} /><span className="max-w-full truncate text-xs text-muted-foreground">v{item.version.version_number}</span></div>)}</div>; }

function buildDashboard(repositories) { const history = repositories.flatMap((repository) => repository.versions.map((version) => ({ repository, version }))).sort((left, right) => new Date(right.version.created_at) - new Date(left.version.created_at)); const latest = repositories.map((repository) => ({ repository, version: repository.versions[0] })).filter((item) => item.version); const fileCount = latest.reduce((total, item) => total + item.version.file_count, 0); const sizeBytes = latest.reduce((total, item) => total + item.version.size_bytes, 0); const versionCount = history.length; const readiness = Math.round(repositories.reduce((total, repository) => total + (repository.versions.length ? 100 : 0), 0) / repositories.length); return { repositoryCount: repositories.length, githubCount: repositories.filter((repository) => repository.source_type === "github").length, zipCount: repositories.filter((repository) => repository.source_type !== "github").length, fileCount, sizeBytes, versionCount, readiness, history, activity: history, latestRepository: history[0]?.repository }; }

function RepositoryLoadingState() {
  return (
    <div className="mt-8 grid gap-4 md:grid-cols-2">
      {[0, 1].map((item) => <div key={item} className="h-48 animate-pulse rounded-xl border border-border bg-muted/40" />)}
    </div>
  );
}

function RepositoryError({ error, onRetry }) {
  return (
    <Card className="mt-8 border-red-500/30">
      <CardContent className="flex items-center gap-3 p-6 text-sm">
        <AlertCircle className="size-5 shrink-0 text-red-600" aria-hidden="true" />
        <div className="flex-1">
          <p className="font-medium">We could not load your repositories.</p>
          <p className="mt-1 text-muted-foreground">{error.message}</p>
        </div>
        <Button variant="outline" size="sm" type="button" onClick={() => onRetry()}>Try again</Button>
      </CardContent>
    </Card>
  );
}

function RepositoryEmptyState() {
  return (
    <Card className="mt-8 border-dashed">
      <CardHeader>
        <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary">
          <FolderGit2 className="size-5" aria-hidden="true" />
        </span>
        <CardTitle className="mt-3">No repositories yet</CardTitle>
        <CardDescription>Start with a public GitHub URL or a ZIP archive from your computer.</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild>
          <Link to="/repositories/new">
            <Plus className="size-4" aria-hidden="true" />
            Import repository
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
