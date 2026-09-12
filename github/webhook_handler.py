"""GitHub Webhook event listener and dispatcher."""

from __future__ import annotations
import hashlib
import hmac
import os
from typing import Any, Dict, Optional
from devrel_guard.agent.graph import guard_agent
from devrel_guard.github.client import GitHubClient


def verify_webhook_signature(payload_bytes: bytes, signature_header: Optional[str], secret: str) -> bool:
    """Verify GitHub webhook payload HMAC-SHA256 signature."""
    if not signature_header or not secret:
        return False
    if not signature_header.startswith("sha256="):
        return False

    expected_sig = "sha256=" + hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_sig, signature_header)


class WebhookHandler:
    """Processes incoming GitHub webhook events and coordinates PR analysis."""

    def __init__(self, github_client: Optional[GitHubClient] = None) -> None:
        self.client = github_client or GitHubClient()

    def process_pr_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pull_request event (opened, synchronize, reopened)."""
        action = payload.get("action")
        if action not in ("opened", "synchronize", "reopened"):
            return {"status": "ignored", "reason": f"Action '{action}' does not require PR scan"}

        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})

        owner = repo.get("owner", {}).get("login")
        repo_name = repo.get("name")
        pr_number = pr.get("number")
        head_sha = pr.get("head", {}).get("sha")

        if not owner or not repo_name or not pr_number or not head_sha:
            return {"status": "error", "reason": "Missing required PR metadata"}

        # 1. Fetch PR Diff
        raw_diff = self.client.fetch_pr_diff(owner, repo_name, pr_number)

        # 2. Invoke LangGraph agent
        initial_state = {
            "raw_diff": raw_diff,
            "source_files": {},
            "step_history": [],
        }
        final_state = guard_agent.invoke(initial_state)

        # 3. Post review to GitHub
        comments = final_state.get("review_comments", [])
        summary = final_state.get("summary_markdown", "")
        passed = final_state.get("passed", True)

        review_event = "APPROVE" if passed else "COMMENT"
        review_res = self.client.submit_pull_request_review(
            owner=owner,
            repo=repo_name,
            pull_number=pr_number,
            commit_id=head_sha,
            summary_markdown=summary,
            inline_comments=comments,
            event=review_event,
        )

        return {
            "status": "success",
            "passed": passed,
            "violations_count": len(final_state.get("violations", [])),
            "review_id": review_res.get("id"),
        }
