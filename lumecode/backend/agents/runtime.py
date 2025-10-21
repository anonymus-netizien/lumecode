import os
import uuid
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from datetime import datetime

from .base import BaseAgent, AgentStatus, AgentType

logger = logging.getLogger(__name__)

class RuntimeStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    TERMINATED = "terminated"

class AgentRuntime:
    """
    Runtime environment for executing agents.
    Manages agent lifecycle, execution context, and resource constraints.
    """
    
    def __init__(self, 
                 workspace_dir: str = None, 
                 max_concurrent_agents: int = 5,
                 max_execution_time: int = 300,  # 5 minutes
                 max_memory_mb: int = 512):
        """
        Initialize the agent runtime.
        
        Args:
            workspace_dir: Directory for agent workspace files
            max_concurrent_agents: Maximum number of agents that can run concurrently
            max_execution_time: Maximum execution time per agent in seconds
            max_memory_mb: Maximum memory usage per agent in MB
        """
        self.workspace_dir = workspace_dir or os.path.join(os.getcwd(), "agent_workspace")
        self.max_concurrent_agents = max_concurrent_agents
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        
        # Create workspace directory if it doesn't exist
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        # Dictionary to track running agents
        self.running_agents: Dict[str, Dict[str, Any]] = {}
        
        # Runtime status
        self.status = RuntimeStatus.IDLE
        
        # Event loop
        self.loop = asyncio.get_event_loop()
        
        logger.info(f"Agent runtime initialized with workspace: {self.workspace_dir}")
    
    async def start_agent(self, 
                         agent: BaseAgent, 
                         context: Dict[str, Any] = None, 
                         callback: Callable[[str, Dict[str, Any]], None] = None) -> str:
        """
        Start an agent with the given context.
        
        Args:
            agent: The agent to start
            context: Context data for the agent
            callback: Callback function to call when the agent completes
            
        Returns:
            Agent execution ID
        """
        # Check if we can run more agents
        if len(self.running_agents) >= self.max_concurrent_agents:
            raise RuntimeError(f"Cannot start agent: maximum concurrent agents ({self.max_concurrent_agents}) reached")
        
        # Generate a unique ID for this execution
        execution_id = str(uuid.uuid4())
        
        # Create agent workspace
        agent_workspace = os.path.join(self.workspace_dir, execution_id)
        os.makedirs(agent_workspace, exist_ok=True)
        
        # Update runtime status
        if self.status == RuntimeStatus.IDLE:
            self.status = RuntimeStatus.RUNNING
        
        # Prepare execution context
        execution_context = {
            "id": execution_id,
            "agent": agent,
            "context": context or {},
            "workspace": agent_workspace,
            "status": AgentStatus.PENDING,
            "start_time": datetime.now(),
            "end_time": None,
            "result": None,
            "error": None,
            "callback": callback,
            "task": None  # Will hold the asyncio task
        }
        
        # Store in running agents
        self.running_agents[execution_id] = execution_context
        
        # Create and start the task
        task = self.loop.create_task(self._run_agent_with_timeout(execution_id))
        execution_context["task"] = task
        
        logger.info(f"Started agent {agent.__class__.__name__} with execution ID {execution_id}")
        
        return execution_id
    
    async def _run_agent_with_timeout(self, execution_id: str) -> None:
        """
        Run an agent with a timeout.
        
        Args:
            execution_id: The execution ID of the agent to run
        """
        if execution_id not in self.running_agents:
            logger.error(f"Agent with execution ID {execution_id} not found")
            return
        
        execution_context = self.running_agents[execution_id]
        agent = execution_context["agent"]
        context = execution_context["context"]
        workspace = execution_context["workspace"]
        
        # Update status
        execution_context["status"] = AgentStatus.RUNNING
        
        try:
            # Run the agent with a timeout
            result = await asyncio.wait_for(
                agent.run(context, workspace),
                timeout=self.max_execution_time
            )
            
            # Update execution context with result
            execution_context["status"] = AgentStatus.COMPLETED
            execution_context["result"] = result
            execution_context["end_time"] = datetime.now()
            
            logger.info(f"Agent {agent.__class__.__name__} completed successfully")
            
            # Call callback if provided
            if execution_context["callback"]:
                try:
                    execution_context["callback"](execution_id, result)
                except Exception as e:
                    logger.error(f"Error in agent callback: {e}")
        
        except asyncio.TimeoutError:
            # Agent execution timed out
            execution_context["status"] = AgentStatus.ERROR
            execution_context["error"] = f"Agent execution timed out after {self.max_execution_time} seconds"
            execution_context["end_time"] = datetime.now()
            
            logger.error(f"Agent {agent.__class__.__name__} timed out after {self.max_execution_time} seconds")
            
            # Attempt to terminate the agent
            try:
                await agent.terminate()
            except Exception as e:
                logger.error(f"Error terminating agent: {e}")
        
        except Exception as e:
            # Agent execution failed
            execution_context["status"] = AgentStatus.ERROR
            execution_context["error"] = str(e)
            execution_context["end_time"] = datetime.now()
            
            logger.error(f"Agent {agent.__class__.__name__} failed: {e}")
        
        finally:
            # Clean up if needed
            self._check_runtime_status()
    
    def _check_runtime_status(self) -> None:
        """
        Check and update the runtime status based on running agents.
        """
        # Count agents that are still running
        running_count = sum(1 for ctx in self.running_agents.values() 
                          if ctx["status"] == AgentStatus.RUNNING or ctx["status"] == AgentStatus.PENDING)
        
        # Update status if no agents are running
        if running_count == 0 and self.status == RuntimeStatus.RUNNING:
            self.status = RuntimeStatus.IDLE
            logger.info("All agents completed, runtime is now idle")
    
    async def stop_agent(self, execution_id: str) -> bool:
        """
        Stop a running agent.
        
        Args:
            execution_id: The execution ID of the agent to stop
            
        Returns:
            True if the agent was stopped, False otherwise
        """
        if execution_id not in self.running_agents:
            logger.warning(f"Agent with execution ID {execution_id} not found")
            return False
        
        execution_context = self.running_agents[execution_id]
        agent = execution_context["agent"]
        
        # Only stop if the agent is running or pending
        if execution_context["status"] in [AgentStatus.RUNNING, AgentStatus.PENDING]:
            # Cancel the task if it exists
            if execution_context["task"] and not execution_context["task"].done():
                execution_context["task"].cancel()
            
            # Try to terminate the agent
            try:
                await agent.terminate()
            except Exception as e:
                logger.error(f"Error terminating agent: {e}")
            
            # Update status
            execution_context["status"] = AgentStatus.TERMINATED
            execution_context["end_time"] = datetime.now()
            
            logger.info(f"Agent {agent.__class__.__name__} stopped")
            
            # Update runtime status
            self._check_runtime_status()
            
            return True
        else:
            logger.warning(f"Cannot stop agent with status {execution_context['status']}")
            return False
    
    def get_agent_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an agent.
        
        Args:
            execution_id: The execution ID of the agent
            
        Returns:
            Agent status information or None if not found
        """
        if execution_id not in self.running_agents:
            return None
        
        execution_context = self.running_agents[execution_id]
        
        # Create a copy of the context without the agent and task objects
        status_info = {
            "id": execution_context["id"],
            "agent_type": execution_context["agent"].__class__.__name__,
            "status": execution_context["status"].value,
            "start_time": execution_context["start_time"].isoformat(),
            "workspace": execution_context["workspace"]
        }
        
        # Add end time if available
        if execution_context["end_time"]:
            status_info["end_time"] = execution_context["end_time"].isoformat()
        
        # Add result if available
        if execution_context["result"]:
            status_info["result"] = execution_context["result"]
        
        # Add error if available
        if execution_context["error"]:
            status_info["error"] = execution_context["error"]
        
        return status_info
    
    def list_agents(self, status_filter: Optional[AgentStatus] = None) -> List[Dict[str, Any]]:
        """
        List all agents, optionally filtered by status.
        
        Args:
            status_filter: Filter agents by this status
            
        Returns:
            List of agent status information
        """
        result = []
        
        for execution_id in self.running_agents:
            status_info = self.get_agent_status(execution_id)
            
            # Apply filter if provided
            if status_filter is None or self.running_agents[execution_id]["status"] == status_filter:
                result.append(status_info)
        
        return result
    
    async def cleanup(self, remove_workspaces: bool = False) -> None:
        """
        Clean up the runtime, stopping all running agents.
        
        Args:
            remove_workspaces: Whether to remove agent workspaces
        """
        # Stop all running agents
        for execution_id in list(self.running_agents.keys()):
            execution_context = self.running_agents[execution_id]
            
            if execution_context["status"] in [AgentStatus.RUNNING, AgentStatus.PENDING]:
                await self.stop_agent(execution_id)
        
        # Remove workspaces if requested
        if remove_workspaces and os.path.exists(self.workspace_dir):
            import shutil
            try:
                shutil.rmtree(self.workspace_dir)
                logger.info(f"Removed agent workspace directory: {self.workspace_dir}")
            except Exception as e:
                logger.error(f"Error removing workspace directory: {e}")
        
        # Update status
        self.status = RuntimeStatus.TERMINATED
        logger.info("Agent runtime terminated")