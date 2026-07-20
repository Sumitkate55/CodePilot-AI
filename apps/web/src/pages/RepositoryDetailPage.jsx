import {
  AlertCircle,
  ArrowLeft,
  ArrowUp,
  BarChart3,
  Braces,
  Clock3,
  Database,
  FileCode2,
  GitCommitHorizontal,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { lazy, Suspense } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatBytes, formatDate } from "@/features/repositories/formatters";
import { ExplainCodePanel } from "@/features/repositories/ExplainCodePanel";
import { RefactoringAdvisorPanel } from "@/features/repositories/RefactoringAdvisorPanel";
import { CodeReviewPanel } from "@/features/repositories/CodeReviewPanel";
import { DocumentationPanel } from "@/features/repositories/DocumentationPanel";
import { RepositoryChatPanel } from "@/features/repositories/RepositoryChatPanel";
import { TestGeneratorPanel } from "@/features/repositories/TestGeneratorPanel";
import {
  useRepository,
  useRepositoryAnalysis,
  useRepositoryArchitectureGraph,
  useRepositoryAnalysisRun,
  useRepositoryDeletion,
  useRepositoryChat,
  useRepositoryChatIndex,
  useRepositoryChatIndexing,
  useRepositoryFunctions,
  useCodeExplanation,
  useRepositoryCodeReview,
  useRepositoryCodeReviewRun,
  useRefactoringDashboard,
  useRefactorProposalDecision,
  useRefactorProposalGeneration,
  useProjectSummary,
  useProjectSummaryGeneration,
  useRepositoryDocumentation,
  useRepositoryDocumentationGeneration,
  useTestGenerationDashboard,
  useUnitTestGeneration,
} from "@/features/repositories/repository-queries";

const ArchitectureGraphPanel = lazy(() => import("@/features/repositories/ArchitectureGraphPanel").then(
  ({ ArchitectureGraphPanel: Component }) => ({ default: Component }),
));

export function RepositoryDetailPage() {
  const { repositoryId } = useParams();
  const navigate = useNavigate();
  const { data: repository, error, isLoading } = useRepository(repositoryId);
  const { data: analysis, error: analysisError, isLoading: isAnalysisLoading } = useRepositoryAnalysis(repositoryId);
  const { data: architectureGraph, error: architectureGraphError, isLoading: isArchitectureGraphLoading } = useRepositoryArchitectureGraph(repositoryId);
  const analysisRun = useRepositoryAnalysisRun();
  const { data: projectSummary, error: projectSummaryError, isLoading: isProjectSummaryLoading } = useProjectSummary(repositoryId);
  const projectSummaryGeneration = useProjectSummaryGeneration();
  const { data: chatIndex, error: chatIndexError } = useRepositoryChatIndex(repositoryId);
  const chatIndexing = useRepositoryChatIndexing();
  const repositoryChat = useRepositoryChat();
  const { data: repositoryFunctions, error: repositoryFunctionsError, isLoading: isRepositoryFunctionsLoading } = useRepositoryFunctions(repositoryId);
  const codeExplanation = useCodeExplanation();
  const { data: codeReview, error: codeReviewError, isLoading: isCodeReviewLoading } = useRepositoryCodeReview(repositoryId);
  const codeReviewRun = useRepositoryCodeReviewRun();
  const { data: refactoringDashboard, error: refactoringError, isLoading: isRefactoringLoading } = useRefactoringDashboard(repositoryId);
  const refactorProposalGeneration = useRefactorProposalGeneration();
  const refactorProposalDecision = useRefactorProposalDecision();
  const { data: testGenerationDashboard, error: testGenerationError, isLoading: isTestGenerationLoading } = useTestGenerationDashboard(repositoryId);
  const unitTestGeneration = useUnitTestGeneration();
  const { data: documentation, error: documentationError, isLoading: isDocumentationLoading } = useRepositoryDocumentation(repositoryId);
  const documentationGeneration = useRepositoryDocumentationGeneration();
  const deletion = useRepositoryDeletion();

  const handleDelete = async () => {
    if (!window.confirm(`Delete ${repository.name} and all of its stored versions? This cannot be undone.`)) {
      return;
    }
    await deletion.mutateAsync(repository.id);
    navigate("/dashboard", { replace: true });
  };

  const handleAnalyze = async () => {
    await analysisRun.mutateAsync(repository.id);
  };

  const handleProjectSummary = async () => {
    await projectSummaryGeneration.mutateAsync(repository.id);
  };

  const handleCodeReview = async () => {
    await codeReviewRun.mutateAsync(repository.id);
  };

  const handleGenerateRefactor = async (findingKey) => {
    await refactorProposalGeneration.mutateAsync({ repositoryId: repository.id, findingKey });
  };

  const handleRefactorDecision = async (proposalId, status) => {
    await refactorProposalDecision.mutateAsync({ repositoryId: repository.id, proposalId, status });
  };

  const handleUnitTestGeneration = async (target) => {
    await unitTestGeneration.mutateAsync({
      repositoryId: repository.id,
      path: target.function.path,
      line: target.function.line,
    });
  };

  const handleDocumentationGeneration = async () => {
    await documentationGeneration.mutateAsync(repository.id);
  };

  if (isLoading) {
    return <div className="h-64 animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (error?.status === 404) {
    return <Navigate to="/dashboard" replace />;
  }
  if (error) {
    return <RepositoryDetailError message={error.message} />;
  }
  if (!repository) {
    return null;
  }

  return (
    <section className="mx-auto max-w-5xl">
      <Button asChild variant="ghost" size="sm">
        <Link to="/dashboard"><ArrowLeft className="size-4" aria-hidden="true" />Back to repositories</Link>
      </Button>
      <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-primary">Repository</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{repository.name}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{repository.remote_url ?? "Uploaded ZIP archive"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" type="button" disabled={projectSummaryGeneration.isPending} onClick={handleProjectSummary}>
            <Sparkles className={projectSummaryGeneration.isPending ? "size-4 animate-pulse" : "size-4"} aria-hidden="true" />
            {projectSummaryGeneration.isPending ? "Generating summary" : projectSummary ? "Refresh summary" : "Generate summary"}
          </Button>
          <Button type="button" disabled={analysisRun.isPending} onClick={handleAnalyze}>
            <RefreshCw className={analysisRun.isPending ? "size-4 animate-spin" : "size-4"} aria-hidden="true" />
            {analysisRun.isPending ? "Analyzing" : analysis ? "Refresh intelligence" : "Analyze repository"}
          </Button>
          <Button variant="outline" type="button" disabled={codeReviewRun.isPending} onClick={handleCodeReview}>
            <ShieldCheck className={codeReviewRun.isPending ? "size-4 animate-pulse" : "size-4"} aria-hidden="true" />
            {codeReviewRun.isPending ? "Reviewing" : codeReview ? "Refresh review" : "Run review"}
          </Button>
          <Button variant="outline" type="button" disabled={deletion.isPending} onClick={handleDelete}>
            <Trash2 className="size-4 text-red-600" aria-hidden="true" />
            {deletion.isPending ? "Deleting" : "Delete repository"}
          </Button>
        </div>
      </div>
      {deletion.error ? <p className="mt-5 rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{deletion.error.message}</p> : null}
      {analysisRun.error ? <p className="mt-5 rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{analysisRun.error.message}</p> : null}
      {projectSummaryGeneration.error ? <p className="mt-5 rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{projectSummaryGeneration.error.message}</p> : null}
      {codeReviewRun.error ? <p className="mt-5 rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{codeReviewRun.error.message}</p> : null}
      <RepositoryFeatureNavigator />
      <div id="summary" className="scroll-mt-28"><ProjectSummary
        summary={projectSummary}
        error={projectSummaryError}
        isLoading={isProjectSummaryLoading}
        onGenerate={handleProjectSummary}
        isGenerating={projectSummaryGeneration.isPending}
      /></div>
      <div id="chat" className="scroll-mt-28"><RepositoryChatPanel
        repositoryId={repository.id}
        index={chatIndex}
        indexError={chatIndexError}
        indexMutation={chatIndexing}
        chatMutation={repositoryChat}
      /></div>
      <div id="architecture" className="scroll-mt-28"><Suspense fallback={<div className="mt-8 h-112 animate-pulse rounded-xl border border-border bg-muted/40" />}>
        <ArchitectureGraphPanel
          repositoryId={repository.id}
          graph={architectureGraph}
          error={architectureGraphError}
          isLoading={isArchitectureGraphLoading}
        />
      </Suspense></div>
      <div id="explain" className="scroll-mt-28"><ExplainCodePanel
        repositoryId={repository.id}
        functions={repositoryFunctions}
        error={repositoryFunctionsError}
        isLoading={isRepositoryFunctionsLoading}
        explanationMutation={codeExplanation}
      /></div>
      <div id="review" className="scroll-mt-28"><CodeReviewPanel
        review={codeReview}
        error={codeReviewError}
        isLoading={isCodeReviewLoading}
        reviewMutation={codeReviewRun}
        onReview={handleCodeReview}
      /></div>
      <div id="refactor" className="scroll-mt-28"><RefactoringAdvisorPanel
        repositoryId={repository.id}
        dashboard={refactoringDashboard}
        error={refactoringError}
        isLoading={isRefactoringLoading}
        proposalMutation={refactorProposalGeneration}
        decisionMutation={refactorProposalDecision}
        onGenerate={handleGenerateRefactor}
        onDecision={handleRefactorDecision}
      /></div>
      <div id="tests" className="scroll-mt-28"><TestGeneratorPanel
        dashboard={testGenerationDashboard}
        error={testGenerationError}
        isLoading={isTestGenerationLoading}
        generationMutation={unitTestGeneration}
        onGenerate={handleUnitTestGeneration}
      /></div>
      <div id="docs" className="scroll-mt-28"><DocumentationPanel
        documentation={documentation}
        error={documentationError}
        isLoading={isDocumentationLoading}
        generationMutation={documentationGeneration}
        onGenerate={handleDocumentationGeneration}
      /></div>
      <div id="intelligence" className="scroll-mt-28"><RepositoryIntelligence
        analysis={analysis}
        error={analysisError}
        isLoading={isAnalysisLoading}
        onAnalyze={handleAnalyze}
        isAnalyzing={analysisRun.isPending}
      /></div>
      <Card id="history" className="mt-8 scroll-mt-28">
        <CardHeader>
          <CardTitle>Import history</CardTitle>
          <CardDescription>Every accepted source import is retained as an immutable version.</CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="divide-y divide-border">
            {repository.versions.map((version) => (
              <li key={version.id} className="grid gap-4 py-5 sm:grid-cols-[auto_1fr_auto] sm:items-center">
                <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary"><FileCode2 className="size-5" aria-hidden="true" /></span>
                <div>
                  <p className="font-medium">Version {version.version_number}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{version.file_count.toLocaleString()} files · {formatBytes(version.size_bytes)} · {formatDate(version.created_at)}</p>
                  {version.commit_sha ? <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground"><GitCommitHorizontal className="size-3.5" aria-hidden="true" />{version.commit_sha}</p> : null}
                </div>
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Clock3 className="size-3.5" aria-hidden="true" />{version.source_type === "github" ? "GitHub" : "ZIP upload"}</span>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </section>
  );
}

const repositoryFeatures = [
  ["summary", "Summary"], ["chat", "Chat"], ["architecture", "Architecture"],
  ["explain", "Explain code"], ["review", "Review"], ["refactor", "Refactor"],
  ["tests", "Tests"], ["docs", "Docs"], ["intelligence", "Intelligence"], ["history", "History"],
];

function RepositoryFeatureNavigator() {
  return <nav className="sticky top-3 z-20 mt-6 rounded-xl border border-border bg-background/95 p-2 shadow-sm backdrop-blur" aria-label="Repository tools"><div className="flex items-center gap-1 overflow-x-auto"><span className="shrink-0 px-2 text-xs font-semibold text-muted-foreground">Jump to</span>{repositoryFeatures.map(([id, label]) => <a key={id} href={`#${id}`} className="shrink-0 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">{label}</a>)}<a href="#top" onClick={(event) => { event.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }); }} className="ml-auto flex shrink-0 items-center gap-1 rounded-md bg-primary/10 px-2.5 py-1.5 text-xs font-medium text-primary"><ArrowUp className="size-3" />Top</a></div></nav>;
}

const summarySections = [
  ["Overview", "overview"],
  ["Architecture", "architecture"],
  ["Features", "features"],
  ["Frontend flow", "frontend_flow"],
  ["Backend flow", "backend_flow"],
  ["Database flow", "database_flow"],
  ["Authentication flow", "authentication_flow"],
  ["API flow", "api_flow"],
];

function ProjectSummary({ summary, error, isLoading, onGenerate, isGenerating }) {
  if (isLoading) {
    return <div className="mt-8 h-72 animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (!summary) {
    if (error && error.status !== 404) {
      return <RepositoryDetailError message={`We could not load the project summary: ${error.message}`} />;
    }
    return (
      <Card className="mt-8 border-dashed">
        <CardHeader>
          <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><Sparkles className="size-5" aria-hidden="true" /></span>
          <CardTitle className="mt-3">AI project summary</CardTitle>
          <CardDescription>Generate an AI summary grounded in the latest repository intelligence, including architecture, features, and application flows.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" disabled={isGenerating} onClick={onGenerate}>
            <Sparkles className="size-4" aria-hidden="true" />
            Generate project summary
          </Button>
        </CardContent>
      </Card>
    );
  }

  const content = summary.content ?? {};
  const limitations = content.limitations ?? [];
  return (
    <Card className="mt-8">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-primary">AI project summary</p>
            <CardTitle className="mt-1">Repository briefing</CardTitle>
            <CardDescription className="mt-1">Generated {formatDate(summary.updated_at)} from the latest repository intelligence.</CardDescription>
          </div>
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">{summary.model}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-5 lg:grid-cols-2">
          {summarySections.map(([title, key]) => <SummarySection key={key} title={title} section={content[key]} />)}
        </div>
        {limitations.length > 0 ? <div className="rounded-lg border border-border bg-muted/30 p-4"><h3 className="text-sm font-semibold">Summary limitations</h3><ul className="mt-2 space-y-1 text-sm text-muted-foreground">{limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div> : null}
      </CardContent>
    </Card>
  );
}

function SummarySection({ title, section }) {
  if (!section) {
    return null;
  }
  return (
    <div className="rounded-lg border border-border p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 whitespace-pre-line text-sm leading-6 text-muted-foreground">{section.summary}</p>
      {section.evidence?.length > 0 ? <ul className="mt-3 space-y-1 text-xs text-muted-foreground">{section.evidence.map((item) => <li key={item}>• {item}</li>)}</ul> : null}
    </div>
  );
}

function RepositoryIntelligence({ analysis, error, isLoading, onAnalyze, isAnalyzing }) {
  if (isLoading) {
    return <div className="mt-8 h-64 animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (!analysis) {
    if (error && error.status !== 404) {
      return <RepositoryDetailError message={`We could not load repository intelligence: ${error.message}`} />;
    }
    return (
      <Card className="mt-8 border-dashed">
        <CardHeader>
          <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><BarChart3 className="size-5" aria-hidden="true" /></span>
          <CardTitle className="mt-3">Repository intelligence is ready to generate</CardTitle>
          <CardDescription>Detect languages, frameworks, dependencies, source symbols, services, database artifacts, and deployment files from the stored source version.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" disabled={isAnalyzing} onClick={onAnalyze}>
            <BarChart3 className="size-4" aria-hidden="true" />
            Analyze latest version
          </Button>
        </CardContent>
      </Card>
    );
  }

  const results = analysis.results ?? {};
  const statistics = results.statistics ?? {};
  const languages = results.languages ?? [];
  const frameworks = results.frameworks ?? [];
  const dependencies = results.dependencies ?? [];
  const services = results.services ?? [];
  const databaseArtifacts = results.database_artifacts ?? [];
  const environmentFiles = results.environment_files ?? [];
  const dockerFiles = results.docker_files ?? [];
  const folders = results.folder_structure ?? [];

  return (
    <Card className="mt-8">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-primary">Latest version intelligence</p>
            <CardTitle className="mt-1">Repository profile</CardTitle>
            <CardDescription className="mt-1">Analyzed {formatDate(analysis.updated_at)} from the latest stored source version.</CardDescription>
          </div>
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">Analysis v{analysis.analysis_version}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-7">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <IntelligenceStat label="Files" value={analysis.file_count} />
          <IntelligenceStat label="Lines" value={analysis.line_count} />
          <IntelligenceStat label="Classes" value={statistics.class_count ?? 0} />
          <IntelligenceStat label="Functions" value={statistics.function_count ?? 0} />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <IntelligenceSection icon={Braces} title="Languages & frameworks">
            <div className="flex flex-wrap gap-2">
              {languages.map((language) => <Tag key={language.name} label={`${language.name} · ${language.files} files`} />)}
              {frameworks.map((framework) => <Tag key={framework} label={framework} tone="primary" />)}
              {languages.length === 0 && frameworks.length === 0 ? <EmptyText>No source languages or frameworks detected.</EmptyText> : null}
            </div>
          </IntelligenceSection>
          <IntelligenceSection icon={Database} title="Data and deployment">
            <div className="space-y-2 text-sm text-muted-foreground">
              <SignalLine label="Database artifacts" value={databaseArtifacts.length} />
              <SignalLine label="Services" value={services.length} />
              <SignalLine label="Environment files" value={environmentFiles.length} />
              <SignalLine label="Docker files" value={dockerFiles.length} />
            </div>
          </IntelligenceSection>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <IntelligenceList title="Dependencies" items={dependencies.slice(0, 12).map((dependency) => `${dependency.name}${dependency.version ? ` ${dependency.version}` : ""}`)} empty="No package manifests were detected." />
          <IntelligenceList title="Deployment & environment files" items={[...dockerFiles, ...environmentFiles]} empty="No Docker or environment files were detected." />
        </div>
        <IntelligenceList title="Top-level structure" items={folders.filter((folder) => folder.path !== ".").slice(0, 10).map((folder) => `${folder.path} · ${folder.file_count} files`)} empty="No nested folders were detected." />
      </CardContent>
    </Card>
  );
}

function IntelligenceStat({ label, value }) {
  return <div className="rounded-lg border border-border bg-muted/30 p-4"><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-semibold">{Number(value ?? 0).toLocaleString()}</p></div>;
}

function IntelligenceSection({ icon: Icon, title, children }) {
  return <div><div className="mb-3 flex items-center gap-2"><Icon className="size-4 text-primary" aria-hidden="true" /><h3 className="text-sm font-semibold">{title}</h3></div>{children}</div>;
}

function IntelligenceList({ title, items, empty }) {
  return <div><h3 className="text-sm font-semibold">{title}</h3>{items.length > 0 ? <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">{items.map((item) => <li key={item} className="truncate">{item}</li>)}</ul> : <EmptyText>{empty}</EmptyText>}</div>;
}

function SignalLine({ label, value }) {
  return <p className="flex items-center justify-between gap-4"><span>{label}</span><span className="font-medium text-foreground">{Number(value).toLocaleString()}</span></p>;
}

function Tag({ label, tone = "default" }) {
  return <span className={tone === "primary" ? "rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary" : "rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground"}>{label}</span>;
}

function EmptyText({ children }) {
  return <p className="mt-2 text-sm text-muted-foreground">{children}</p>;
}

function RepositoryDetailError({ message }) {
  return (
    <Card className="border-red-500/30">
      <CardContent className="flex items-center gap-3 p-6 text-sm"><AlertCircle className="size-5 text-red-600" aria-hidden="true" /><span>{message}</span></CardContent>
    </Card>
  );
}
