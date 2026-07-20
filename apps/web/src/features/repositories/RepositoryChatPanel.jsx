import { useState } from "react";
import { Bot, Database, FileCode2, RefreshCw, Send, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const suggestedQuestions = [
  "Where is the application entry point?",
  "How is authentication implemented?",
  "Which files define the API routes?",
];

export function RepositoryChatPanel({ repositoryId, index, indexError, indexMutation, chatMutation }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const ready = index?.status === "ready";

  const handleIndex = async () => {
    await indexMutation.mutateAsync(repositoryId);
  };

  const handleAsk = async (event) => {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || chatMutation.isPending) {
      return;
    }
    const answer = await chatMutation.mutateAsync({ repositoryId, question: trimmedQuestion });
    setMessages((current) => [...current, { question: trimmedQuestion, answer }]);
    setQuestion("");
  };

  const unavailableMessage = indexError && indexError.status !== 404 ? indexError.message : null;

  return (
    <Card className="mt-8">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-primary">Repository chat</p>
            <CardTitle className="mt-1">Ask your codebase</CardTitle>
            <CardDescription className="mt-1">Answers are restricted to retrieved repository source and include file-and-line citations.</CardDescription>
          </div>
          {ready ? <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-700">{index.chunk_count.toLocaleString()} chunks indexed</span> : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {unavailableMessage ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{unavailableMessage}</p> : null}
        {indexMutation.error ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{indexMutation.error.message}</p> : null}
        {chatMutation.error ? <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-700" role="alert">{chatMutation.error.message}</p> : null}

        {!ready ? (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-5">
            <div className="flex gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary"><Database className="size-5" aria-hidden="true" /></span>
              <div>
                <h3 className="font-medium">Index this repository for chat</h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">Safe text files are chunked and embedded in Qdrant. Environment and credential-like files are excluded.</p>
                <Button className="mt-4" type="button" disabled={indexMutation.isPending} onClick={handleIndex}>
                  <Sparkles className={indexMutation.isPending ? "size-4 animate-pulse" : "size-4"} aria-hidden="true" />
                  {indexMutation.isPending ? "Indexing repository" : "Index repository"}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
              <span>Only the latest stored repository version is searchable.</span>
              <Button variant="ghost" size="sm" type="button" disabled={indexMutation.isPending} onClick={handleIndex}>
                <RefreshCw className={indexMutation.isPending ? "size-4 animate-spin" : "size-4"} aria-hidden="true" />
                Reindex
              </Button>
            </div>
            {messages.length === 0 ? (
              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.map((suggestion) => <Button key={suggestion} variant="outline" size="sm" type="button" onClick={() => setQuestion(suggestion)}>{suggestion}</Button>)}
              </div>
            ) : null}
            <div className="space-y-4">
              {messages.map((message, indexPosition) => <ChatMessage key={`${message.question}-${indexPosition}`} message={message} />)}
            </div>
            <form className="flex flex-col gap-2 sm:flex-row" onSubmit={handleAsk}>
              <label className="sr-only" htmlFor="repository-question">Ask a repository question</label>
              <input id="repository-question" className="min-h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring" maxLength={4000} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about this repository…" />
              <Button type="submit" disabled={!question.trim() || chatMutation.isPending}>
                <Send className="size-4" aria-hidden="true" />
                {chatMutation.isPending ? "Searching" : "Ask"}
              </Button>
            </form>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ChatMessage({ message }) {
  const { answer } = message;
  return (
    <div className="space-y-3 rounded-xl border border-border p-4">
      <p className="text-sm font-medium">{message.question}</p>
      <div className="flex gap-3 text-sm leading-6 text-muted-foreground">
        <Bot className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
        <p>{answer.answer}</p>
      </div>
      {answer.citations?.length > 0 ? (
        <div className="space-y-2 border-t border-border pt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Sources</p>
          {answer.citations.map((citation) => <Citation key={citation.source_id} citation={citation} />)}
        </div>
      ) : <p className="text-xs text-muted-foreground">No source supports a more specific answer.</p>}
    </div>
  );
}

function Citation({ citation }) {
  return (
    <details className="rounded-lg border border-border bg-muted/20 p-3">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-medium">
        <FileCode2 className="size-4 text-primary" aria-hidden="true" />
        <span className="min-w-0 truncate">{citation.path}</span>
        <span className="ml-auto shrink-0 text-xs font-normal text-muted-foreground">Lines {citation.start_line}–{citation.end_line}</span>
      </summary>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded bg-background p-3 text-xs leading-5 text-muted-foreground">{citation.excerpt}</pre>
    </details>
  );
}
