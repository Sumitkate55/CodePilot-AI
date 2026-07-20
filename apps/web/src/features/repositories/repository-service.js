import { apiClient } from "@/services/api-client";

export async function listRepositories() {
  const { data } = await apiClient.get("/repositories");
  return data;
}

export async function getRepository(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}`);
  return data;
}

export async function importGitHubRepository(payload) {
  const { data } = await apiClient.post("/repositories/import/github", payload);
  return data;
}

export async function uploadRepositoryArchive({ file, repositoryName }) {
  const formData = new FormData();
  formData.append("file", file);
  if (repositoryName) {
    formData.append("repository_name", repositoryName);
  }
  const { data } = await apiClient.post("/repositories/upload", formData);
  return data;
}

export async function deleteRepository(repositoryId) {
  await apiClient.delete(`/repositories/${repositoryId}`);
}

export async function getRepositoryAnalysis(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/analysis`);
  return data;
}

export async function getRepositoryArchitectureGraph(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/architecture-graph`);
  return data;
}

export async function getRepositoryFunctions(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/functions`);
  return data;
}

export async function explainRepositoryCode({ repositoryId, path, line }) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/explain-code`, { path, line });
  return data;
}

export async function getRepositoryCodeReview(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/review`);
  return data;
}

export async function reviewRepositoryCode(repositoryId) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/review`);
  return data;
}

export async function getRefactoringDashboard(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/refactoring`);
  return data;
}

export async function generateRefactorProposal({ repositoryId, findingKey }) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/refactoring/proposals`, { finding_key: findingKey });
  return data;
}

export async function decideRefactorProposal({ repositoryId, proposalId, status }) {
  const { data } = await apiClient.patch(`/repositories/${repositoryId}/refactoring/proposals/${proposalId}`, { status });
  return data;
}

export async function getTestGenerationDashboard(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/test-generation`);
  return data;
}

export async function generateUnitTests({ repositoryId, path, line }) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/test-generation`, { path, line });
  return data;
}

export async function getRepositorySourceFile(repositoryId, path) {
  const encodedPath = path.split("/").map(encodeURIComponent).join("/");
  const { data } = await apiClient.get(`/repositories/${repositoryId}/files/${encodedPath}`);
  return data;
}

export async function analyzeRepository(repositoryId) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/analyze`);
  return data;
}

export async function getProjectSummary(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/summary`);
  return data;
}

export async function generateProjectSummary(repositoryId) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/summary`);
  return data;
}

export async function getRepositoryDocumentation(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/documentation`);
  return data;
}

export async function generateRepositoryDocumentation(repositoryId) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/documentation`);
  return data;
}

export async function getRepositoryChatIndex(repositoryId) {
  const { data } = await apiClient.get(`/repositories/${repositoryId}/chat/index`);
  return data;
}

export async function indexRepositoryForChat(repositoryId) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/chat/index`);
  return data;
}

export async function askRepositoryChat({ repositoryId, question }) {
  const { data } = await apiClient.post(`/repositories/${repositoryId}/chat`, { question });
  return data;
}
