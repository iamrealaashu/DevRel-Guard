"""Command Line Interface for DevRel Guard."""

from __future__ import annotations
import os
import sys
import time
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from devrel_guard.agent.graph import guard_agent
from devrel_guard.core.models import GuardReport
from devrel_guard.rules.catalog import catalog

console = Console()

# Pre-packaged realistic benchmark scenarios
BENCHMARK_SCENARIOS = {
    "pydantic": {
        "title": "PR #104: Upgrade Pydantic from 1.10.12 to 2.8.2",
        "diff": """diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,3 +1,3 @@
 fastapi==0.110.0
-pydantic==1.10.12
+pydantic==2.8.2
 uvicorn==0.28.0
diff --git a/app/models.py b/app/models.py
--- a/app/models.py
+++ b/app/models.py
@@ -1,8 +1,8 @@
-from pydantic import BaseModel, validator
+from pydantic import BaseModel, validator
 
 class UserProfile(BaseModel):
     name: str
     email: str
 
     @validator('name')
     def validate_name(cls, v):
         return v.strip()
""",
        "files": {
            "app/models.py": """from pydantic import BaseModel, validator

class UserProfile(BaseModel):
    name: str
    email: str

    @validator('name')
    def validate_name(cls, v):
        return v.strip()

def serialize_user(user: UserProfile):
    return user.dict()
""",
        },
    },
    "langchain": {
        "title": "PR #215: Upgrade LangChain from 0.1.0 to 0.2.5",
        "diff": """diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,2 +1,2 @@
-langchain==0.1.0
+langchain==0.2.5
 openai>=1.0.0
diff --git a/agent/bot.py b/agent/bot.py
--- a/agent/bot.py
+++ b/agent/bot.py
@@ -1,3 +1,3 @@
-from langchain.chat_models import ChatOpenAI
+from langchain.chat_models import ChatOpenAI
""",
        "files": {
            "agent/bot.py": """from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings

def run_agent_pipeline(query: str):
    llm = ChatOpenAI(model="gpt-4o")
    return chain.run(query)
""",
        },
    },
    "openai": {
        "title": "PR #340: Upgrade OpenAI Python SDK from 0.28.1 to 1.12.0",
        "diff": """diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,2 +1,2 @@
-openai==0.28.1
+openai==1.12.0
 pydantic>=2.0.0
diff --git a/services/llm.py b/services/llm.py
--- a/services/llm.py
+++ b/services/llm.py
@@ -1,4 +1,4 @@
 import openai
""",
        "files": {
            "services/llm.py": """import openai

def generate_summary(text: str):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": text}]
    )
    return response.choices[0].message.content
""",
        },
    },
}


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """DevRel Guard: Autonomous PR & Dependency Breaking-Change Agent."""
    pass


@main.command()
@click.option("--scenario", type=click.Choice(["pydantic", "langchain", "openai", "all"]), default="pydantic")
def simulate(scenario: str) -> None:
    """Run an interactive simulation against realistic breaking change benchmarks."""
    console.print(
        Panel.fit(
            "[bold cyan]🛡️ DevRel Guard[/bold cyan] [white]• Autonomous PR Breaking-Change Simulation[/white]\n"
            "[dim]LangGraph Agentic CI/CD Bot with Static AST Analysis[/dim]",
            border_style="cyan",
        )
    )

    scenarios_to_run = list(BENCHMARK_SCENARIOS.keys()) if scenario == "all" else [scenario]

    for sc_key in scenarios_to_run:
        sc = BENCHMARK_SCENARIOS[sc_key]
        console.print(f"\n[bold yellow]▶ Simulating Scenario:[/bold yellow] [bold white]{sc['title']}[/bold white]")

        # Show Diff
        console.print(Panel(Syntax(sc["diff"], "diff", theme="monokai", line_numbers=True), title="PR Unified Diff", border_style="dim"))

        start_t = time.time()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Initializing LangGraph agent...", total=None)
            time.sleep(0.3)

            progress.update(task, description="[cyan]Node 1: Scanning PR diff & dependency manifests...")
            time.sleep(0.3)

            progress.update(task, description="[cyan]Node 2: Mining breaking change rules & deprecations...")
            time.sleep(0.3)

            progress.update(task, description="[cyan]Node 3: Static AST inspection across source code...")
            time.sleep(0.3)

            progress.update(task, description="[cyan]Node 4: Agentic refactoring synthesizing AST patches...")
            time.sleep(0.3)

            progress.update(task, description="[cyan]Node 5: Verifying AST syntax and patch soundness...")
            time.sleep(0.3)

            progress.update(task, description="[cyan]Node 6: Formatting inline GitHub suggestions...")

            # Run actual LangGraph agent
            initial_state = {
                "raw_diff": sc["diff"],
                "source_files": sc["files"],
                "step_history": [],
            }
            res = guard_agent.invoke(initial_state)

        duration = time.time() - start_t

        # 1. Dependency Table
        dep_table = Table(title="📦 Upgraded Dependencies", border_style="blue")
        dep_table.add_column("Package", style="bold")
        dep_table.add_column("Old Version")
        dep_table.add_column("New Version")
        dep_table.add_column("Bump Type")

        for d in res.get("dependency_changes", []):
            bump_color = "red" if d.is_major_bump else "green"
            dep_table.add_row(
                d.package_name,
                d.old_version,
                f"[bold {bump_color}]{d.new_version}[/bold {bump_color}]",
                "🚨 BREAKING / MAJOR" if d.is_major_bump else "Minor/Patch",
            )
        console.print(dep_table)

        # 2. Violations Table
        v_list = res.get("violations", [])
        if v_list:
            v_table = Table(title="🚨 AST Breaking Change Violations", border_style="red")
            v_table.add_column("File:Line", style="bold yellow")
            v_table.add_column("Symbol", style="bold cyan")
            v_table.add_column("Rule ID", style="dim")
            v_table.add_column("Severity")

            for v in v_list:
                sev_color = "bold red" if v.rule.severity.value == "CRITICAL" else "yellow"
                v_table.add_row(
                    f"{v.file_path}:{v.line_number}",
                    v.symbol,
                    v.rule.id,
                    f"[{sev_color}]{v.rule.severity.value}[/{sev_color}]",
                )
            console.print(v_table)

        # 3. Inline GitHub Suggestions
        comments = res.get("review_comments", [])
        if comments:
            console.print("\n[bold green]💬 Generated GitHub PR Inline Suggestions:[/bold green]")
            for c in comments:
                console.print(
                    Panel(
                        f"[bold]{c.path}:{c.line}[/bold]\n\n{c.body}",
                        title=f"GitHub PR Inline Review Comment (`{c.path}`)",
                        border_style="green",
                    )
                )

        console.print(
            f"[dim]Completed in {duration:.2f}s • {res.get('nodes_scanned', 0)} AST nodes scanned • Status: {'✅ CLEAN' if res.get('passed') else '⚠️ ACTION REQUIRED'}[/dim]\n"
        )


@main.command()
@click.option("--repo", default=".", help="Path to repository root.")
@click.option("--diff", default=None, help="Path to unified diff file.")
def scan(repo: str, diff: Optional[str]) -> None:
    """Scan local repository or diff for dependency breaking changes."""
    raw_diff = ""
    if diff and os.path.exists(diff):
        with open(diff, "r", encoding="utf-8") as f:
            raw_diff = f.read()

    console.print(f"[bold cyan]Scanning repository:[/bold cyan] {os.path.abspath(repo)}")
    initial_state = {
        "raw_diff": raw_diff,
        "repo_root": os.path.abspath(repo),
        "source_files": {},
        "step_history": [],
    }

    result = guard_agent.invoke(initial_state)
    console.print(result.get("summary_markdown", ""))

    if not result.get("passed", True):
        sys.exit(1)


@main.command()
@click.option("--repo", default=".", help="Path to repository root.")
@click.option("--diff", default=None, help="Path to unified diff file.")
@click.option("--apply", "apply_changes", is_flag=True, default=False, help="Apply verified refactored patches directly to disk.")
def fix(repo: str, diff: Optional[str], apply_changes: bool) -> None:
    """Analyze and apply verified code fixes for dependency breaking changes."""
    raw_diff = ""
    if diff and os.path.exists(diff):
        with open(diff, "r", encoding="utf-8") as f:
            raw_diff = f.read()

    abs_repo = os.path.abspath(repo)
    console.print(f"[bold cyan]Auditing and refactoring codebase:[/bold cyan] {abs_repo}")
    initial_state = {
        "raw_diff": raw_diff,
        "repo_root": abs_repo,
        "source_files": {},
        "step_history": [],
    }

    result = guard_agent.invoke(initial_state)
    refactored = result.get("refactored_files", {})
    fixes = result.get("verified_fixes") or result.get("fixes", [])

    if not fixes:
        console.print("[bold green]✅ No breaking changes detected. Nothing to fix![/bold green]")
        return

    console.print(f"\n[bold yellow]Found {len(fixes)} breaking call-sites across {len(refactored)} files.[/bold yellow]")

    for file_path, new_content in refactored.items():
        full_path = os.path.join(abs_repo, file_path) if not os.path.isabs(file_path) else file_path
        if apply_changes:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            console.print(f"[bold green]✔ Applied verified patch to:[/bold green] {file_path}")
        else:
            console.print(f"[bold cyan]Proposed changes for:[/bold cyan] {file_path} [dim](use --apply to write to disk)[/dim]")

    if apply_changes:
        console.print("\n[bold green]🎉 All verified patches successfully written to disk![/bold green]")


@main.command()
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", default=8080, type=int, help="Bind port")
def serve(host: str, port: int) -> None:
    """Launch the Webhook server and interactive Web Dashboard."""
    import uvicorn
    from devrel_guard.server.app import app

    console.print(
        Panel.fit(
            f"[bold green]🛡️ DevRel Guard Server Starting[/bold green]\n"
            f"• Web Dashboard: [bold cyan]http://localhost:{port}[/bold cyan]\n"
            f"• GitHub Webhook: [bold cyan]http://localhost:{port}/api/webhook[/bold cyan]\n"
            f"• REST API Docs: [bold cyan]http://localhost:{port}/docs[/bold cyan]",
            border_style="green",
        )
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
