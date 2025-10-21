from typing import Dict, List, Any, Optional, Callable, Awaitable
import logging
from abc import ABC, abstractmethod
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


class BaseAgent(ABC):
    """
    Base class for all Lumecode agents.
    """

    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.result = None
        self.error = None
        logger.info(f"Initializing agent {self.agent_id}")

    @abstractmethod
    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent with the provided context.

        Args:
            context: Context data for the agent to work with

        Returns:
            Results of the agent's work
        """
        pass

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent, handling status updates and errors.
        """
        try:
            self.status = AgentStatus.RUNNING
            logger.info(f"Agent {self.agent_id} started execution")

            result = await self.run(context)

            self.result = result
            self.status = AgentStatus.COMPLETED
            logger.info(f"Agent {self.agent_id} completed successfully")

            return result
        except Exception as e:
            self.error = str(e)
            self.status = AgentStatus.FAILED
            logger.error(f"Agent {self.agent_id} failed: {e}", exc_info=True)
            raise

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent.
        """
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


class AgentRegistry:
    """
    Registry for managing and accessing available agents.
    """

    def __init__(self):
        self.agents: Dict[str, type] = {}

    def register(self, agent_type: str, agent_class: type):
        """
        Register an agent class with the registry.
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"Agent class must be a subclass of BaseAgent")

        self.agents[agent_type] = agent_class
        logger.info(f"Registered agent type: {agent_type}")

    def get_agent_class(self, agent_type: str) -> type:
        """
        Get an agent class by type.
        """
        if agent_type not in self.agents:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return self.agents[agent_type]

    def create_agent(
        self,
        agent_type: str,
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """
        Create an instance of an agent by type.
        """
        agent_class = self.get_agent_class(agent_type)
        return agent_class(agent_id=agent_id, config=config)

    def list_agent_types(self) -> List[str]:
        """
        List all registered agent types.
        """
        return list(self.agents.keys())


# Create a global agent registry
agent_registry = AgentRegistry()
