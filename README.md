# 🛡️ DevRel Guard

> **Autonomous PR & Dependency Breaking-Change Agent**

DevRel Guard is an AI-powered developer workflow tool that analyzes pull requests for dependency-related breaking changes, inspects affected Python code with AST analysis, proposes safe refactors, verifies the generated patches, and formats actionable GitHub-style review comments.

Built around a **LangGraph agent workflow**, DevRel Guard can be used from the command line or through its FastAPI web dashboard/API.

## ✨ Features

- 🔎 **PR diff analysis** — parses unified diffs and identifies dependency changes.
- 📦 **Dependency breaking-change detection** — checks upgraded packages against an ecosystem rule catalog.
- 🌳 **Python AST inspection** — finds affected imports, symbols, calls, and usage patterns in source code.
- 🤖 **Agentic refactoring** — synthesizes code changes for detected breaking call-sites.
- ✅ **Patch verification** — validates proposed fixes before they are applied.
- 💬 **GitHub-style review comments** — produces inline suggestions with file and line references.
- 🧪 **Built-in benchmark scenarios** — includes Pydantic, LangChain, and OpenAI SDK upgrade simulations.
- 💻 **CLI workflow** — scan repositories, simulate scenarios, apply verified fixes, or start the server.
- 🌐 **FastAPI API & dashboard** — exposes scanning, rules, scenarios, and GitHub webhook endpoints.
- 🔗 **GitHub webhook support** — accepts `pull_request` events and can verify webhook signatures.

## 🧠 How It Works

DevRel Guard runs a multi-step LangGraph workflow:

```text
PR Diff
   │
   ▼
┌────────────────────┐
│  Scan PR / Deps    │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Mine Changelog /   │
│ Breaking Rules     │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Python AST Inspect │
└─────────┬──────────┘
          │
     Violations?
       /      \
     Yes       No
      │         │
      ▼         ▼
┌───────────┐  ┌──────────────┐
│ Refactor  │  │ Format PR    │
│ Code      │  │ Review       │
└─────┬─────┘  └──────┬───────┘
      ▼               │
┌───────────┐         │
│ Verify    │─────────┘
│ Patches   │
└───────────┘
```

The workflow is implemented as a compiled LangGraph state machine with dedicated nodes for diff scanning, changelog/rule mining, AST inspection, refactoring, verification, and PR review formatting.

## 🏗️ Project Structure

```text
DevRel-Guard/
├── agent/
│   ├── graph.py          # LangGraph workflow definition
│   ├── llm.py            # LLM integration
│   ├── nodes.py          # Agent workflow nodes
│   └── state.py           # Shared agent state
│
├── core/
│   ├── ast_inspector.py   # Python AST analysis
│   ├── changelog_miner.py # Breaking-change/rule discovery
│   ├── dep_scanner.py     # Dependency change detection
│   ├── diff_parser.py     # Unified diff parsing
│   ├── models.py          # Data models
│   ├── pr_formatter.py    # PR review formatting
│   ├── refactorer.py      # Refactor generation
│   └── verifier.py        # Patch verification
│
├── demo/                  # Demo/benchmark assets
├── rules/                 # Ecosystem breaking-change rule catalog
├── server/
│   └── app.py             # FastAPI API, dashboard & webhook server
├── cli.py                 # Command-line interface
└── README.md
```

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/iamrealaashu/DevRel-Guard.git
cd DevRel-Guard
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

Install the project's Python dependencies using the dependency file included in your checkout, or install the required packages for your environment.

Typical runtime components used by the project include:

- Python 3.10+
- LangGraph
- FastAPI
- Uvicorn
- Click
- Rich
- Pydantic

If the project uses environment variables for your LLM/provider integration, configure them before running the agent.

## 🖥️ CLI Usage

The CLI exposes four main commands: `simulate`, `scan`, `fix`, and `serve`.

### Run a benchmark simulation

```bash
python cli.py simulate --scenario pydantic
```

Available scenarios:

```bash
python cli.py simulate --scenario pydantic
python cli.py simulate --scenario langchain
python cli.py simulate --scenario openai
python cli.py simulate --scenario all
```

The simulation prints the PR diff, upgraded dependencies, AST violations, generated GitHub-style review comments, and execution details.

### Scan a repository

```bash
python cli.py scan --repo .
```

To analyze a unified diff file:

```bash
python cli.py scan --repo . --diff path/to/change.diff
```

A failed analysis exits with a non-zero status, which makes the command suitable for CI pipelines.

### Generate and apply verified fixes

Preview proposed changes:

```bash
python cli.py fix --repo .
```

Apply verified patches to disk:

```bash
python cli.py fix --repo . --apply
```

## 🌐 Web Dashboard & API

Start the FastAPI server:

```bash
python cli.py serve
```

By default, the server binds to `0.0.0.0:8080`.

Custom host and port:

```bash
python cli.py serve --host 127.0.0.1 --port 8080
```

Once running:

- Dashboard: `http://localhost:8080/`
- API documentation: `http://localhost:8080/docs`
- Scan API: `POST /api/scan`
- Rules API: `GET /api/rules`
- Benchmark scenarios: `GET /api/scenarios`
- GitHub webhook: `POST /api/webhook`

### Scan API example

```bash
curl -X POST http://localhost:8080/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "diff": "<unified diff here>",
    "files": {
      "app/models.py": "<source code here>"
    }
  }'
```

The API returns structured information including:

```json
{
  "passed": false,
  "duration_seconds": 0.42,
  "nodes_scanned": 123,
  "dependency_changes": [],
  "violations": [],
  "fixes": [],
  "review_comments": [],
  "refactored_files": {},
  "summary_markdown": "...",
  "step_history": []
}
```

## 🔗 GitHub Webhooks

DevRel Guard includes a webhook endpoint for GitHub `pull_request` events.

Configure your webhook to point to:

```text
POST /api/webhook
```

For production deployments, set the webhook secret as an environment variable:

```bash
export GITHUB_WEBHOOK_SECRET="your-secret"
```

The server verifies the `X-Hub-Signature-256` signature when a secret is configured.

> **Production note:** expose the webhook through HTTPS and place the service behind an appropriate reverse proxy or ingress before connecting it to a production GitHub repository.

## 🧪 Example Use Cases

### Dependency upgrade safety

A pull request upgrades a package such as:

```text
pydantic 1.x → 2.x
```

DevRel Guard can inspect the upgrade, identify affected APIs such as deprecated validators or serialization methods, propose a compatible refactor, verify the result, and generate a review summary.

### CI/CD quality gate

Run `scan` in CI and fail the job when unresolved breaking-change violations are found:

```bash
python cli.py scan --repo . --diff changes.diff
```

### Automated developer feedback

Connect the webhook endpoint to GitHub so incoming pull-request events can be analyzed and converted into structured review feedback.

## 🔐 Configuration

The exact LLM/provider configuration depends on the model integration used by your environment. Keep API keys and webhook secrets in environment variables or another secure secret-management system.

Never commit credentials, API keys, or webhook secrets to the repository.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| **Python** | Core implementation |
| **LangGraph** | Agent workflow orchestration |
| **FastAPI** | REST API and webhook server |
| **Uvicorn** | ASGI server |
| **Click** | CLI framework |
| **Rich** | Terminal UI and reports |
| **Python AST** | Static source-code inspection |
| **Pydantic** | Data validation and structured models |
| **GitHub Webhooks** | Pull-request event integration |

## 📌 Current Status

DevRel Guard is an evolving project focused on automated dependency-upgrade analysis and developer tooling. The repository currently includes the agent workflow, AST/dependency analysis components, CLI, API server, benchmark scenarios, and GitHub webhook handling.

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch:

```bash
git checkout -b feature/my-change
```

3. Make your changes.
4. Run the relevant simulations and scans.
5. Commit your work:

```bash
git commit -m "feat: improve breaking-change detection"
```

6. Push the branch and open a pull request.

For larger changes, consider opening an issue first to discuss the design.

## 📄 License

No license file is currently included in the repository. Until a license is added, assume that the repository's code is **not granted broad open-source reuse rights** beyond the permissions provided by applicable law.

## 🌟 Acknowledgements

DevRel Guard combines static analysis, dependency intelligence, agentic workflows, and developer-facing automation to make dependency upgrades safer and easier to review.

---

<p align="center">
  Built with ❤️ for safer dependency upgrades and better developer workflows.
</p>
