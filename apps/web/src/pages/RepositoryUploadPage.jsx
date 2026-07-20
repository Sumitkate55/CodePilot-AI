import { ArrowLeft, FileArchive, Github, LoaderCircle, UploadCloud } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  useGitHubImport,
  useRepositoryArchiveUpload,
} from "@/features/repositories/repository-queries";

const githubSchema = z.object({
  github_url: z.string().trim().url("Enter a complete GitHub HTTPS URL."),
  display_name: z.string().trim().max(120).optional(),
});

export function RepositoryUploadPage() {
  const [sourceType, setSourceType] = useState("github");

  return (
    <section className="mx-auto max-w-2xl">
      <Button asChild variant="ghost" size="sm">
        <Link to="/dashboard">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to repositories
        </Link>
      </Button>
      <div className="mt-5">
        <p className="text-sm font-medium text-primary">Repository intake</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Add a repository</h1>
        <p className="mt-2 text-muted-foreground">
          Import a public GitHub repository or upload a ZIP archive. Every import is retained as a version.
        </p>
      </div>
      <div className="mt-8 grid grid-cols-2 rounded-lg bg-muted p-1" role="tablist" aria-label="Repository source">
        <SourceTab active={sourceType === "github"} onClick={() => setSourceType("github")} icon={Github} label="GitHub URL" />
        <SourceTab active={sourceType === "zip"} onClick={() => setSourceType("zip")} icon={FileArchive} label="ZIP upload" />
      </div>
      <Card className="mt-4">
        {sourceType === "github" ? <GitHubImportForm /> : <ZipUploadForm />}
      </Card>
      <p className="mt-4 text-xs leading-5 text-muted-foreground">
        ZIP archives are checked for unsafe paths, symbolic links, compression bombs, and size limits before storage.
      </p>
    </section>
  );
}

function SourceTab({ active, icon: Icon, label, onClick }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={active ? "flex items-center justify-center gap-2 rounded-md bg-card px-3 py-2 text-sm font-medium shadow-sm" : "flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground"}
    >
      <Icon className="size-4" aria-hidden="true" />
      {label}
    </button>
  );
}

function GitHubImportForm() {
  const navigate = useNavigate();
  const mutation = useGitHubImport();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(githubSchema), defaultValues: { github_url: "", display_name: "" } });

  const submit = async (values) => {
    const payload = { ...values, display_name: values.display_name || undefined };
    const repository = await mutation.mutateAsync(payload);
    navigate(`/repositories/${repository.id}`);
  };

  return (
    <form onSubmit={handleSubmit(submit)} noValidate>
      <CardHeader>
        <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><Github className="size-5" aria-hidden="true" /></span>
        <CardTitle className="mt-3">Import from GitHub</CardTitle>
        <CardDescription>Use a public HTTPS URL in the format https://github.com/owner/repository.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <FormField label="GitHub repository URL" error={errors.github_url?.message}>
          <Input type="url" autoComplete="url" placeholder="https://github.com/owner/repository" aria-invalid={Boolean(errors.github_url)} {...register("github_url")} />
        </FormField>
        <FormField label="Display name (optional)" error={errors.display_name?.message}>
          <Input placeholder="Use repository name" aria-invalid={Boolean(errors.display_name)} {...register("display_name")} />
        </FormField>
        <MutationError error={mutation.error} />
        <Button className="w-full" size="lg" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Github className="size-4" aria-hidden="true" />}
          {mutation.isPending ? "Cloning repository" : "Clone repository"}
        </Button>
      </CardContent>
    </form>
  );
}

function ZipUploadForm() {
  const navigate = useNavigate();
  const mutation = useRepositoryArchiveUpload();
  const [file, setFile] = useState(null);
  const [repositoryName, setRepositoryName] = useState("");
  const [validationError, setValidationError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    if (!file) {
      setValidationError("Choose a ZIP archive to continue.");
      return;
    }
    setValidationError("");
    const repository = await mutation.mutateAsync({ file, repositoryName });
    navigate(`/repositories/${repository.id}`);
  };

  return (
    <form onSubmit={submit}>
      <CardHeader>
        <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><UploadCloud className="size-5" aria-hidden="true" /></span>
        <CardTitle className="mt-3">Upload a ZIP archive</CardTitle>
        <CardDescription>The archive filename becomes the repository name unless you provide one.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <label className="grid gap-2 text-sm font-medium">
          ZIP archive
          <Input
            type="file"
            accept=".zip,application/zip"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            aria-invalid={Boolean(validationError)}
          />
          <span className="text-xs font-normal text-muted-foreground">{file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : "Choose a .zip file"}</span>
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Display name (optional)
          <Input value={repositoryName} onChange={(event) => setRepositoryName(event.target.value)} placeholder="Use archive filename" />
        </label>
        {validationError ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{validationError}</p> : null}
        <MutationError error={mutation.error} />
        <Button className="w-full" size="lg" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <UploadCloud className="size-4" aria-hidden="true" />}
          {mutation.isPending ? "Uploading archive" : "Upload repository"}
        </Button>
      </CardContent>
    </form>
  );
}

function FormField({ label, error, children }) {
  return (
    <label className="grid gap-2 text-sm font-medium">
      {label}
      {children}
      {error ? <span className="text-xs text-red-600">{error}</span> : null}
    </label>
  );
}

function MutationError({ error }) {
  return error ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{error.message}</p> : null;
}
