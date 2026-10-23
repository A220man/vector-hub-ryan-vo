"""Git worktree operations service."""
import os
import shutil
import subprocess
import asyncio
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from app.config import settings


@dataclass
class GitOperationResult:
    """Result of a git operation."""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0


class GitError(Exception):
    """Git operation error."""
    pass


class GitService:
    """Service for git worktree operations."""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or settings.git_worktree_base)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.shared_dirs = [d.strip() for d in settings.git_shared_dirs.split(",") if d.strip()]

    def _setup_shared_dirs(self, repo_path: Path, worktree_path: Path) -> None:
        """Create symlinks for shared directories in the worktree."""
        for shared_dir in self.shared_dirs:
            source = repo_path / shared_dir
            target = worktree_path / shared_dir
            if source.exists() and source.is_dir() and not target.exists():
                try:
                    target.symlink_to(source, target_is_directory=True)
                except (OSError, FileExistsError):
                    pass  # Ignore symlink errors

    def clone_project(self, git_url: str, target_path: Path, base_ref: str = "main") -> GitOperationResult:
        """Clone a project at a specific ref."""
        if target_path.exists():
            return GitOperationResult(success=False, error=f"Path {target_path} already exists")

        result = GitOperationResult(success=False)

        # Clone with depth=1 initial
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", git_url, str(target_path)],
            capture_output=True, text=True, timeout=300
        )
        result.exit_code = proc.returncode
        result.output = proc.stdout
        result.error = proc.stderr

        if proc.returncode != 0:
            result.success = False
            # Clean up partial clone
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            return result

        # Fetch the specific ref to ensure it's available
        proc = subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", base_ref],
            capture_output=True, text=True, timeout=120,
            cwd=str(target_path)
        )
        if proc.returncode != 0:
            result.output += "\n" + proc.stdout
            result.error = proc.stderr
            # Non-fatal: ref might already be checked out

        # Checkout the base ref
        proc = subprocess.run(
            ["git", "checkout", base_ref],
            capture_output=True, text=True, timeout=60,
            cwd=str(target_path)
        )
        result.output += "\n" + proc.stdout
        result.error += "\n" + proc.stderr
        result.exit_code = proc.returncode
        result.success = proc.returncode == 0

        return result

    def create_worktree(self, repo_path: Path, branch: str, start_ref: str, worktree_name: str) -> GitOperationResult:
        """Create a git worktree."""
        worktree_path = self.base_path / worktree_name

        if worktree_path.exists():
            return GitOperationResult(
                success=False,
                error=f"Worktree path {worktree_path} already exists"
            )

        # Ensure start_ref exists
        proc = subprocess.run(
            ["git", "checkout", start_ref],
            capture_output=True, text=True, timeout=30,
            cwd=str(repo_path)
        )
        if proc.returncode != 0:
            # Check if repo has remotes
            proc_remotes = subprocess.run(
                ["git", "remote"],
                capture_output=True, text=True, timeout=10,
                cwd=str(repo_path)
            )
            has_remotes = bool(proc_remotes.stdout.strip())
            
            if has_remotes:
                # Try fetching from origin
                proc = subprocess.run(
                    ["git", "fetch", "origin", start_ref],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(repo_path)
                )
                if proc.returncode != 0:
                    return GitOperationResult(
                        success=False,
                        error=f"Cannot fetch {start_ref} from origin: {proc.stderr}",
                        exit_code=proc.returncode
                    )
                subprocess.run(
                    ["git", "checkout", start_ref],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(repo_path)
                )
            else:
                # No remotes - try to checkout local branch
                proc = subprocess.run(
                    ["git", "checkout", start_ref],
                    capture_output=True, text=True, timeout=30,
                    cwd=str(repo_path)
                )
                if proc.returncode != 0:
                    return GitOperationResult(
                        success=False,
                        error=f"Cannot checkout {start_ref} (no remotes): {proc.stderr}",
                        exit_code=proc.returncode
                    )

        # Create the worktree with a new branch
        proc = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(worktree_path), start_ref],
            capture_output=True, text=True, timeout=120,
            cwd=str(repo_path)
        )

        if proc.returncode != 0:
            return GitOperationResult(
                success=False,
                output=proc.stdout,
                error=proc.stderr,
                exit_code=proc.returncode
            )

        # Verify the worktree is valid
        proc = subprocess.run(
            ["git", "worktree", "list"],
            capture_output=True, text=True, timeout=10,
            cwd=str(repo_path)
        )

        return GitOperationResult(
            success=True,
            output=proc.stdout,
            error=proc.stdout + proc.stderr,
            exit_code=0
        )

    async def create_worktree_async(self, repo_path: Path, branch: str, start_ref: str, worktree_name: str) -> GitOperationResult:
        """Create a git worktree asynchronously (runs in thread pool)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.create_worktree, repo_path, branch, start_ref, worktree_name)

    def list_worktrees(self, repo_path: Path) -> list[dict]:
        """List worktrees for a repository."""
        proc = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10,
            cwd=str(repo_path)
        )
        if proc.returncode != 0:
            return []

        worktrees = []
        current = {}
        for line in proc.stdout.strip().split("\n"):
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line.replace("worktree ", "")}
            elif line.startswith("HEAD "):
                current["head"] = line.replace("HEAD ", "")
            elif line.startswith("branch "):
                current["branch"] = line.replace("branch ", "").replace("refs/heads/", "")
        if current:
            worktrees.append(current)

        return worktrees

    async def list_worktrees_async(self, repo_path: Path) -> list[dict]:
        """List worktrees for a repository asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.list_worktrees, repo_path)

    def remove_worktree(self, repo_path: Path, worktree_path: Path) -> GitOperationResult:
        """Remove a git worktree."""
        if not worktree_path.exists():
            return GitOperationResult(success=False, error="Worktree path does not exist")

        proc = subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            capture_output=True, text=True, timeout=60,
            cwd=str(repo_path)
        )

        if proc.returncode != 0:
            return GitOperationResult(
                success=False,
                output=proc.stdout,
                error=proc.stderr,
                exit_code=proc.returncode
            )

        # Also remove the branch
        branch_name = Path(worktree_path).name
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            capture_output=True, text=True, timeout=10,
            cwd=str(repo_path)
        )

        # Clean up directory if git didn't
        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)

        return GitOperationResult(success=True)

    async def remove_worktree_async(self, repo_path: Path, worktree_path: Path) -> GitOperationResult:
        """Remove a git worktree asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.remove_worktree, repo_path, worktree_path)

    def prune_worktrees(self, repo_path: Path) -> GitOperationResult:
        """Run git worktree prune to clean up stale worktrees."""
        proc = subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, timeout=30,
            cwd=str(repo_path)
        )
        return GitOperationResult(
            success=proc.returncode == 0,
            output=proc.stdout,
            error=proc.stderr,
            exit_code=proc.returncode
        )

    def get_branch_info(self, repo_path: Path, branch: str) -> Optional[str]:
        """Get the start-from base ref for a branch."""
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(repo_path)
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
        return None
