# Three-minute demo video script

Use the live site at https://codepilot-ai-hackathon.vercel.app and record at 1080p with clear
voice-over. Keep the final public YouTube video under three minutes.

| Time | Screen action | Suggested narration |
| --- | --- | --- |
| 0:00–0:15 | Open the welcome screen. | “I built CodePilot AI, a developer tool that turns an unfamiliar repository into a secure engineering workspace.” |
| 0:15–0:35 | Register or sign in; open **Add repository**. | “Users authenticate before importing a GitHub repository or ZIP. Each stored repository is scoped to its owner.” |
| 0:35–0:55 | Import `https://github.com/Sumitkate55/CodePilot-AI.git` and run analysis. | “CodePilot maps languages, frameworks, dependencies, services, symbols, Docker, and database artifacts without needing an AI model.” |
| 0:55–1:15 | Show statistics and the architecture graph; click a node. | “The architecture graph makes frontend, backend, services, and data relationships navigable.” |
| 1:15–1:35 | Run code review and show severity filters. | “The repository-wide review detects security, performance, naming, dead-code, and maintainability findings with severity and confidence.” |
| 1:35–1:55 | Open refactoring advisor and show a proposal/diff. | “The refactoring advisor turns a finding into a reviewable proposal, with confidence, impact, highlighted code, and an accept-or-reject workflow.” |
| 1:55–2:20 | Generate summary, index, and ask a chat question. | “Safe files are chunked and embedded in private Qdrant. Chat retrieves repository context and answers with file-and-line citations. Environment and credential-like files are excluded before embedding.” |
| 2:20–2:40 | Show generated tests and documentation. | “CodePilot can explain code, generate pytest, Jest, or JUnit tests, and create README, API, installation, and usage documentation.” |
| 2:40–2:58 | Show deployed site and repository. | “I built this in test-backed phases with Codex using GPT-5.6. Codex helped analyze the codebase, preserve Clean Architecture, implement the features, add provider safety, and prepare production deployment.” |

Before recording the AI segment, add `GEMINI_API_KEY` directly in Railway and use a small public
sample repository. Do not show API keys, Railway variables, browser storage, terminal secrets, or
private repositories in the recording.
