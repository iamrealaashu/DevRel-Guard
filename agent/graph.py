"""LangGraph Workflow Graph Construction."""

from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from devrel_guard.agent.state import GuardAgentState
from devrel_guard.agent.nodes import (
    scan_diff_node,
    mine_changelog_node,
    inspect_ast_node,
    refactor_code_node,
    verify_patches_node,
    format_pr_review_node,
)


def route_after_inspection(state: GuardAgentState) -> str:
    """Route to refactoring if violations found, otherwise format review directly."""
    violations = state.get("violations", [])
    if violations:
        return "refactor_code"
    return "format_pr_review"


def create_guard_graph() -> StateGraph:
    """Build and compile the multi-agent DevRel Guard LangGraph state machine."""
    builder = StateGraph(GuardAgentState)

    # 1. Add agent nodes
    builder.add_node("scan_diff", scan_diff_node)
    builder.add_node("mine_changelog", mine_changelog_node)
    builder.add_node("inspect_ast", inspect_ast_node)
    builder.add_node("refactor_code", refactor_code_node)
    builder.add_node("verify_patches", verify_patches_node)
    builder.add_node("format_pr_review", format_pr_review_node)

    # 2. Add edges
    builder.add_edge(START, "scan_diff")
    builder.add_edge("scan_diff", "mine_changelog")
    builder.add_edge("mine_changelog", "inspect_ast")

    # Conditional routing after AST inspection
    builder.add_conditional_edges(
        "inspect_ast",
        route_after_inspection,
        {
            "refactor_code": "refactor_code",
            "format_pr_review": "format_pr_review",
        },
    )

    builder.add_edge("refactor_code", "verify_patches")
    builder.add_edge("verify_patches", "format_pr_review")
    builder.add_edge("format_pr_review", END)

    return builder.compile()


# Pre-compiled graph instance
guard_agent = create_guard_graph()
