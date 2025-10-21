import os
import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from lumecode.backend.agents import BaseAgent, AgentStatus, AgentRuntime, RuntimeStatus

class MockAgent(BaseAgent):
    """Mock agent for testing"""
    
    def __init__(self, delay=0, should_fail=False):
        super().__init__()
        self.delay = delay
        self.should_fail = should_fail
        self.terminated = False
    
    async def execute(self, context=None, workspace=None):
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if self.should_fail:
            raise RuntimeError("Agent failed intentionally")
        
        return {"status": "success", "message": "Agent completed successfully"}
    
    async def terminate(self):
        self.terminated = True

class TestAgentRuntime:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Create a temporary workspace directory
        self.test_workspace = os.path.join(os.path.dirname(__file__), "test_workspace")
        os.makedirs(self.test_workspace, exist_ok=True)
        
        # Create the runtime
        self.runtime = AgentRuntime(
            workspace_dir=self.test_workspace,
            max_concurrent_agents=3,
            max_execution_time=2,  # Short timeout for testing
            max_memory_mb=100
        )
        
        yield
        
        # Clean up the workspace directory
        if os.path.exists(self.test_workspace):
            import shutil
            shutil.rmtree(self.test_workspace)
    
    def test_runtime_initialization(self):
        """Test that the runtime initializes correctly"""
        assert self.runtime.status == RuntimeStatus.IDLE
        assert self.runtime.max_concurrent_agents == 3
        assert self.runtime.max_execution_time == 2
        assert self.runtime.max_memory_mb == 100
        assert self.runtime.workspace_dir == self.test_workspace
    
    @pytest.mark.asyncio
    async def test_start_agent(self):
        """Test starting an agent"""
        agent = MockAgent()
        execution_id = await self.runtime.start_agent(agent)
        
        # Check that the agent was started
        assert execution_id in self.runtime.running_agents
        assert self.runtime.status == RuntimeStatus.RUNNING
        
        # Wait for the agent to complete
        await asyncio.sleep(0.5)
        
        # Check that the agent completed successfully
        status = self.runtime.get_agent_status(execution_id)
        assert status["status"] == AgentStatus.COMPLETED.value
        assert "result" in status
        assert status["result"]["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_agent_timeout(self):
        """Test that an agent times out"""
        agent = MockAgent(delay=3)  # Longer than the timeout
        execution_id = await self.runtime.start_agent(agent)
        
        # Wait for the agent to time out
        await asyncio.sleep(2.5)
        
        # Check that the agent timed out
        status = self.runtime.get_agent_status(execution_id)
        assert status["status"] == AgentStatus.ERROR.value
        assert "error" in status
        assert "timed out" in status["error"]
    
    @pytest.mark.asyncio
    async def test_agent_failure(self):
        """Test that an agent failure is handled correctly"""
        agent = MockAgent(should_fail=True)
        execution_id = await self.runtime.start_agent(agent)
        
        # Wait for the agent to fail
        await asyncio.sleep(0.5)
        
        # Check that the agent failed
        status = self.runtime.get_agent_status(execution_id)
        assert status["status"] == AgentStatus.ERROR.value
        assert "error" in status
        assert "Agent failed intentionally" in status["error"]
    
    @pytest.mark.asyncio
    async def test_stop_agent(self):
        """Test stopping an agent"""
        agent = MockAgent(delay=1)
        execution_id = await self.runtime.start_agent(agent)
        
        # Stop the agent
        result = await self.runtime.stop_agent(execution_id)
        
        # Check that the agent was stopped
        assert result
        status = self.runtime.get_agent_status(execution_id)
        assert status["status"] == AgentStatus.TERMINATED.value
        assert agent.terminated
    
    @pytest.mark.asyncio
    async def test_max_concurrent_agents(self):
        """Test that the maximum number of concurrent agents is enforced"""
        # Start the maximum number of agents
        for i in range(self.runtime.max_concurrent_agents):
            await self.runtime.start_agent(MockAgent(delay=1))
        
        # Try to start one more agent
        with pytest.raises(RuntimeError):
            await self.runtime.start_agent(MockAgent())
    
    @pytest.mark.asyncio
    async def test_list_agents(self):
        """Test listing agents"""
        # Start some agents
        await self.runtime.start_agent(MockAgent())
        await self.runtime.start_agent(MockAgent(should_fail=True))
        
        # Wait for the agents to complete
        await asyncio.sleep(0.5)
        
        # List all agents
        agents = self.runtime.list_agents()
        assert len(agents) == 2
        
        # List completed agents
        completed = self.runtime.list_agents(status_filter=AgentStatus.COMPLETED)
        assert len(completed) == 1
        
        # List failed agents
        failed = self.runtime.list_agents(status_filter=AgentStatus.ERROR)
        assert len(failed) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleaning up the runtime"""
        # Start some agents
        await self.runtime.start_agent(MockAgent(delay=1))
        await self.runtime.start_agent(MockAgent(delay=1))
        
        # Clean up the runtime
        await self.runtime.cleanup(remove_workspaces=True)
        
        # Check that the runtime was terminated
        assert self.runtime.status == RuntimeStatus.TERMINATED
        
        # Check that the workspace was removed
        assert not os.path.exists(self.test_workspace)


if __name__ == "__main__":
    pytest.main([__file__, '-v'])