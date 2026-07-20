import { useEffect, useState } from "react";
import { BookOpenText, CircleAlert, FileText, LoaderCircle, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/features/repositories/formatters";

const documents = [
  ["readme", "README"],
  ["api_reference", "API reference"],
  ["folder_guide", "Folder guide"],
  ["installation_guide", "Installation"],
  ["usage_guide", "Usage"],
];

export function DocumentationPanel({ documentation, error, isLoading, generationMutation, onGenerate }) {
  const [selectedDocument, setSelectedDocument] = useState("readme");
  useEffect(() => {
    if (documentation?.documents && !documentation.documents[selectedDocument]) {
      setSelectedDocument(documents.find(([key]) => documentation.documents[key])?.[0] ?? "readme");
    }
  }, [documentation, selectedDocument]);
  if (isLoading) return <div className="mt-8 h-96 animate-pulse rounded-xl border border-border bg-muted/40" />;
  if (!documentation) {
    const message = error?.status === 404
      ? "Generate a source-grounded documentation bundle for the latest stored repository version."
      : error?.message ?? "Documentation generation is unavailable.";
    return <Card className="mt-8 border-dashed"><CardHeader><span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><BookOpenText className="size-5" aria-hidden="true" /></span><CardTitle className="mt-3">Documentation</CardTitle><CardDescription>{message}</CardDescription></CardHeader><CardContent><GenerateButton mutation={generationMutation} onGenerate={onGenerate} /></CardContent></Card>;
  }
  const markdown = documentation.documents?.[selectedDocument] ?? "No document content was generated.";
  return <Card className="mt-8 overflow-hidden"><CardHeader><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-medium text-primary">Repository documentation</p><CardTitle className="mt-1">Developer-ready Markdown</CardTitle><CardDescription className="mt-1">Generated {formatDate(documentation.updated_at)} from repository intelligence. Copy the Markdown into your repository when ready.</CardDescription></div><span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">{documentation.model}</span></div></CardHeader><CardContent className="space-y-4"><div className="flex flex-wrap gap-2">{documents.map(([key, label]) => <Button key={key} type="button" size="sm" variant={key === selectedDocument ? "default" : "outline"} onClick={() => setSelectedDocument(key)}>{label}</Button>)}</div><div className="overflow-hidden rounded-xl border border-border bg-slate-950 text-slate-100"><p className="flex items-center gap-2 border-b border-slate-700 px-4 py-3 text-sm font-semibold"><FileText className="size-4 text-blue-300" aria-hidden="true" />{documents.find(([key]) => key === selectedDocument)?.[1]}</p><pre className="max-h-112 overflow-auto whitespace-pre-wrap break-words p-4 text-xs leading-6 text-slate-300"><code>{markdown}</code></pre></div>{documentation.notes?.length ? <ul className="space-y-1 text-sm text-muted-foreground">{documentation.notes.map((note) => <li key={note}>• {note}</li>)}</ul> : null}<GenerateButton mutation={generationMutation} onGenerate={onGenerate} label="Regenerate documentation" /></CardContent></Card>;
}

function GenerateButton({ mutation, onGenerate, label = "Generate documentation" }) {
  return <><Button type="button" disabled={mutation.isPending} onClick={onGenerate}>{mutation.isPending ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <Sparkles className="size-4" aria-hidden="true" />}{mutation.isPending ? "Generating documentation" : label}</Button>{mutation.error ? <p className="mt-3 flex items-center gap-2 text-sm text-red-700"><CircleAlert className="size-4" aria-hidden="true" />{mutation.error.message}</p> : null}</>;
}
