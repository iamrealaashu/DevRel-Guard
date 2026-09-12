"""GitHub REST API Client for submitting PR reviews and inline suggestions."""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import requests
from devrel_guard.core.models import PRReviewComment


class GitHubClient:
    """GitHub API client that posts reviews, inline suggestions, and checks."""

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevRel-Guard-Agent",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def fetch_pr_diff(self, owner: str, repo: str, pull_number: int) -> str:
        """Fetch the unified diff of a pull request."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = dict(self.headers)
        headers["Accept"] = "application/vnd.github.v3.diff"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text

    def fetch_pr_files(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """Fetch list of changed files in a pull request."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def submit_pull_request_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_id: str,
        summary_markdown: str,
        inline_comments: List[PRReviewComment],
        event: str = "COMMENT",  # 'APPROVE', 'REQUEST_CHANGES', or 'COMMENT'
    ) -> Dict[str, Any]:
        """Submit a formal PR review with inline ```suggestion comments."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"

        api_comments = []
        for c in inline_comments:
            api_comments.append({
                "path": c.path,
                "line": c.line,
                "side": c.side,
                "body": c.body,
            })

        payload = {
            "commit_id": commit_id,
            "body": summary_markdown,
            "event": event,
            "comments": api_comments,
        }

        resp = requests.post(url, json=payload, headers=self.headers)
        resp.raise_for_status()
        return resp.json()
