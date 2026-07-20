import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  analyzeRepository,
  askRepositoryChat,
  deleteRepository,
  decideRefactorProposal,
  explainRepositoryCode,
  generateUnitTests,
  getRepositoryCodeReview,
  getRefactoringDashboard,
  generateProjectSummary,
  generateRepositoryDocumentation,
  generateRefactorProposal,
  getRepositoryChatIndex,
  getRepositoryAnalysis,
  getRepositoryArchitectureGraph,
  getRepository,
  getRepositoryFunctions,
  getRepositorySourceFile,
  getTestGenerationDashboard,
  getProjectSummary,
  getRepositoryDocumentation,
  importGitHubRepository,
  listRepositories,
  indexRepositoryForChat,
  reviewRepositoryCode,
  uploadRepositoryArchive,
} from "./repository-service";

export const repositoryKeys = {
  all: ["repositories"],
  detail: (repositoryId) => ["repositories", repositoryId],
  analysis: (repositoryId) => ["repositories", repositoryId, "analysis"],
  architectureGraph: (repositoryId) => ["repositories", repositoryId, "architecture-graph"],
  functions: (repositoryId) => ["repositories", repositoryId, "functions"],
  codeReview: (repositoryId) => ["repositories", repositoryId, "code-review"],
  refactoring: (repositoryId) => ["repositories", repositoryId, "refactoring"],
  testGeneration: (repositoryId) => ["repositories", repositoryId, "test-generation"],
  sourceFile: (repositoryId, path) => ["repositories", repositoryId, "source-file", path],
  summary: (repositoryId) => ["repositories", repositoryId, "summary"],
  documentation: (repositoryId) => ["repositories", repositoryId, "documentation"],
  chatIndex: (repositoryId) => ["repositories", repositoryId, "chat-index"],
};

export function useRepositories() {
  return useQuery({ queryKey: repositoryKeys.all, queryFn: listRepositories });
}

export function useRepository(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.detail(repositoryId),
    queryFn: () => getRepository(repositoryId),
    enabled: Boolean(repositoryId),
  });
}

export function useRepositoryAnalysis(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.analysis(repositoryId),
    queryFn: () => getRepositoryAnalysis(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useRepositoryArchitectureGraph(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.architectureGraph(repositoryId),
    queryFn: () => getRepositoryArchitectureGraph(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useRepositoryFunctions(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.functions(repositoryId),
    queryFn: () => getRepositoryFunctions(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useCodeExplanation() {
  return useMutation({ mutationFn: explainRepositoryCode });
}

export function useRepositoryCodeReview(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.codeReview(repositoryId),
    queryFn: () => getRepositoryCodeReview(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useRepositoryCodeReviewRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reviewRepositoryCode,
    onSuccess: (review, repositoryId) => {
      queryClient.setQueryData(repositoryKeys.codeReview(repositoryId), review);
    },
  });
}

export function useRefactoringDashboard(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.refactoring(repositoryId),
    queryFn: () => getRefactoringDashboard(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useRefactorProposalGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateRefactorProposal,
    onSuccess: (_proposal, variables) => {
      queryClient.invalidateQueries({ queryKey: repositoryKeys.refactoring(variables.repositoryId) });
    },
  });
}

export function useRefactorProposalDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: decideRefactorProposal,
    onSuccess: (_proposal, variables) => {
      queryClient.invalidateQueries({ queryKey: repositoryKeys.refactoring(variables.repositoryId) });
    },
  });
}

export function useTestGenerationDashboard(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.testGeneration(repositoryId),
    queryFn: () => getTestGenerationDashboard(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useUnitTestGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateUnitTests,
    onSuccess: (_generatedTest, variables) => {
      queryClient.invalidateQueries({ queryKey: repositoryKeys.testGeneration(variables.repositoryId) });
    },
  });
}

export function useRepositorySourceFile(repositoryId, path) {
  return useQuery({
    queryKey: repositoryKeys.sourceFile(repositoryId, path),
    queryFn: () => getRepositorySourceFile(repositoryId, path),
    enabled: Boolean(repositoryId && path),
    retry: false,
  });
}

export function useProjectSummary(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.summary(repositoryId),
    queryFn: () => getProjectSummary(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

function useRepositoryMutation(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: repositoryKeys.all }),
  });
}

export function useGitHubImport() {
  return useRepositoryMutation(importGitHubRepository);
}

export function useRepositoryArchiveUpload() {
  return useRepositoryMutation(uploadRepositoryArchive);
}

export function useRepositoryDeletion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteRepository,
    onSuccess: (_, repositoryId) => {
      queryClient.removeQueries({ queryKey: repositoryKeys.detail(repositoryId) });
      queryClient.invalidateQueries({ queryKey: repositoryKeys.all });
    },
  });
}

export function useRepositoryAnalysisRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: analyzeRepository,
    onSuccess: (analysis, repositoryId) => {
      queryClient.setQueryData(repositoryKeys.analysis(repositoryId), analysis);
      queryClient.invalidateQueries({ queryKey: repositoryKeys.architectureGraph(repositoryId) });
      queryClient.invalidateQueries({ queryKey: repositoryKeys.functions(repositoryId) });
      queryClient.invalidateQueries({ queryKey: repositoryKeys.codeReview(repositoryId) });
      queryClient.invalidateQueries({ queryKey: repositoryKeys.refactoring(repositoryId) });
      queryClient.invalidateQueries({ queryKey: repositoryKeys.testGeneration(repositoryId) });
    },
  });
}

export function useProjectSummaryGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateProjectSummary,
    onSuccess: (summary, repositoryId) => {
      queryClient.setQueryData(repositoryKeys.summary(repositoryId), summary);
      queryClient.invalidateQueries({ queryKey: repositoryKeys.analysis(repositoryId) });
    },
  });
}

export function useRepositoryDocumentation(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.documentation(repositoryId),
    queryFn: () => getRepositoryDocumentation(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useRepositoryDocumentationGeneration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateRepositoryDocumentation,
    onSuccess: (documentation, repositoryId) => {
      queryClient.setQueryData(repositoryKeys.documentation(repositoryId), documentation);
    },
  });
}

export function useRepositoryChatIndex(repositoryId) {
  return useQuery({
    queryKey: repositoryKeys.chatIndex(repositoryId),
    queryFn: () => getRepositoryChatIndex(repositoryId),
    enabled: Boolean(repositoryId),
    retry: false,
  });
}

export function useRepositoryChatIndexing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: indexRepositoryForChat,
    onSuccess: (index, repositoryId) => {
      queryClient.setQueryData(repositoryKeys.chatIndex(repositoryId), index);
    },
  });
}

export function useRepositoryChat() {
  return useMutation({ mutationFn: askRepositoryChat });
}
