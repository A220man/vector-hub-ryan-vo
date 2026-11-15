"""Tests for AgentService."""
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.agent_service import AgentService, AgentExecutionResult


class TestAgentService:
    """Tests for AgentService class."""

    def test_init_with_custom_base_path(self):
        """Test initialization with custom base path."""
        service = AgentService(worktrees_base="/custom/path")
        assert service.worktrees_base == Path("/custom/path")

    def test_default_base_path(self):
        """Test initialization with default base path."""
        service = AgentService()
        assert service.worktrees_base is not None

    def test_agent_configs_default(self):
        """Test default agent configurations."""
        service = AgentService()
        assert "claude-code" in service.agent_configs
        assert "codex" in service.agent_configs
        assert "opencode" in service.agent_configs

    def test_get_agent_configs(self):
        """Test getting agent configuration."""
        service = AgentService()
        claude_config = service.get_agent_configs("claude-code")
        assert claude_config is not None
        assert claude_config["command"] == "claude"

    def test_get_agent_configs_not_found(self):
        """Test getting non-existent agent configuration."""
        service = AgentService()
        assert service.get_agent_configs("non-existent") is None

    @pytest.mark.asyncio
    async def test_execute_agent_success(self):
        """Test successful agent execution."""
        service = AgentService()
        
        # Mock the asyncio.create_subprocess_exec
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.wait.return_value = 0
        
        # Mock the stream readers
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_subprocess.return_value = mock_process
            
            # Test execution
            result = await service.execute_agent(
                worktree_path=Path("/tmp/test-worktree"),
                agent_name="claude-code",
                command="test-command",
                prompt="test-prompt"
            )
            
            assert isinstance(result, AgentExecutionResult)
            assert result.pid == 12345
            assert result.exit_code == 0
            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_agent_failure(self):
        """Test failed agent execution."""
        service = AgentService()
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.wait.return_value = 1
            
            result = await service.execute_agent(
                worktree_path=Path("/tmp/test-worktree"),
 ∈         agent_name="claude-code",
                command="test-command"
            )
            
            assert isinstance(result, AgentExecutionResult)
            assert result.exit_code == 1
            assert result.success is False

    def test_ensure_worktree_symlinks(self):
        """Test worktree symlink creation."""
        service = AgentService()
        worktree_path = Path("/tmp/worktree")
        shared_dirs = ["node_modules", ".cache"]
        
        # This would test symlink creation in real scenarios
        # For now, just verify the method exists
        service._ensure_worktree_symlinks(worktree_path, shared_dirs)

    def test_log_execution_metrics(self):
        """Test execution metrics logging."""
        service = AgentService()
        
        # Create a mock result
        result = AgentExecutionResult(
            success=True,
            output="test output",
            error="test error",
            exit_code=0,
            pid=12345,
            start_time=pytest.importorskip("datetime").datetime.now(),
            end_time=pytest.importorskip("datetime").datetime.now()
        )
        
        # This would test the metrics logging
        # For now, just verify the method exists
        import asyncio
        asyncio.run(service._log_execution_metrics(
            agent_run_id="test-run-id",
            result=result,
            agent_name="claude-code",
            config={"command": "claude"}
        ))


