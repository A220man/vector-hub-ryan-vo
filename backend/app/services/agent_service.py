"""Agent orchestration service."""
import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent_run import AgentRunStatus


@dataclass
class AgentExecutionResult:
    """Result of an agent execution."""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    pid: Optional[int] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None


class AgentService:
    """Service for executing coding agents in worktrees."""

    def __init__(self, worktrees_base: Optional[str] = None):
        self.worktrees_base = Path(worktrees_base or settings.git_worktree_base)
        self.worktrees_base.mkdir(parents=True, exist_ok=True)
        
        # Agent configurations from settings
        self.agent_configs: Dict[str, Dict[str, Any]] = {
            "claude-code": {
                "command": getattr(settings, "claude_code_command", "claude"),
                "args": getattr(settings, "claude_code_args", []),
                "worktrees": getattr(settings, "claude_code_worktrees", ["node_modules", ".cache"])
            },
            "codex": {
                "command": getattr(settings, "codex_command", "codex"),
                "args": getattr(settings, "codex_args", []),
                "worktrees": getattr(settings, "codex_worktrees", ["node_modules", ".cache"])
            },
            "opencode": {
                "command": getattr(settings, "opencode_command", "opencode"),
                "args": getattr(settings, "opencode_args", []),
                "worktrees": getattr(settings, "opencode_worktrees", ["node_modules", ".cache"])
            }
        }

    async def execute_agent(
        self,
        worktree_path: Path,
        agent_name: str,
        command: Optional[str] = None,
        prompt: Optional[str] = None,
        agent_run_id: Optional[str] = None
    ) -> AgentExecutionResult:
        """
        Execute an agent in a worktree directory.
        
        Args:
            worktree_path: Path to the worktree directory
            agent_name: Name of the agent (claude-code, codex, opencode)
            command: Full command to execute (overrides agent config)
            prompt: Prompt to send to the agent
            agent_run_id: Optional ID for logging/monitoring
            
        Returns:
            AgentExecutionResult with execution details
        """
        # Get agent configuration
        config = self.agent_configs.get(agent_name, self.agent_configs["claude-code"])
        
        # Build command
        cmd = [config["command"]] + config["args"]
        if command:
            cmd.extend(command.split())
        
        # Add prompt if provided
        if prompt:
            cmd.extend(["--prompt", prompt])
        
        # Ensure worktree directory exists and has necessary symlinks
        self._ensure_worktree_symlinks(worktree_path, config["worktrees"])
        
        try:
            # Start process in worktree directory
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(worktree_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                limit=10 * 1024 * 1024  # 10MB buffer limit
            )
            
            result = AgentExecutionResult(
                success=True,
                pid=process.pid,
                output="",
                error=""
            )
            
            # Read output asynchronously
            async def read_stream(stream, buffer):
                try:
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        decoded = line.decode('utf-8', errors='replace')
                        buffer += decoded
                except Exception as e:
                    buffer += f"\n[Stream read error: {e}]\n"
                return buffer
            
            # Read both stdout and stderr concurrently
            output_task = asyncio.create_task(read_stream(process.stdout, result.output))
            error_task = asyncio.create_task(read_stream(process.stderr, result.error))
            
            # Wait for process to complete
            exit_code = await process.wait()
            result.exit_code = exit_code
            result.end_time = datetime.now(timezone.utc)
            
            # Get remaining output
            result.output = await output_task
            result.error = await error_task
            
            # Log execution metrics if agent_run_id provided
            if agent_run_id:
                await self._log_execution_metrics(agent_run_id, result, agent_name, config)
            
            return result
            
        except Exception as e:
            return AgentExecutionResult(
                success=False,
                error=f"Failed to execute agent: {str(e)}",
                exit_code=1
            )

    def _ensure_worktree_symlinks(self, worktree_path: Path, shared_dirs: List[str]) -> None:
        """Create symlinks for shared directories in worktree."""
        for dir_name in shared_dirs:
            source_dir = self.worktrees_base / dir_name
            target_dir = worktree_path / dir_name
            
            if not target_dir.exists():
                try:
                    # Create parent directory if needed
                    target_dir.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Create symlink
                    if source_dir.exists():
                        target_dir.symlink_to(source_dir)
                    else:
                        # Create directory if source doesn't exist
                        target_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    # Don't fail the entire operation for symlink issues
                    pass

    async def _log_execution_metrics(
        self,
        agent_run_id: str,
        result: AgentExecutionResult,
        agent_name: str,
        config: Dict[str, Any]
    ) -> None:
        """Log execution metrics to database."""
        # This would integrate with the database to record metrics
        # For now, just log to a simple metrics store
        metrics = {
            "agent_name": agent_name,
            "duration_seconds": (result.end_time - result.start_time).total_seconds(),
            "exit_code": result.exit_code,
            "output_size_bytes": len(result.output),
            "error_size_bytes": len(result.error),
            "success": result.success
        }
        
        # In a real implementation, this would update the AgentRun record
        # For now, this is a placeholder
        
    def get_agent_configs(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for an agent."""
        return self.agent_configs.get(agent_name)
