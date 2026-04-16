"""
Base Tool abstract class for Agentic RAG system.

All retrieval tools must inherit from this base class.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standard result format for all tools."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """
    Abstract base class for all retrieval tools.

    Each tool must implement:
    - name: Unique identifier for the tool
    - description: Human-readable description for Agent selection
    - execute(): Main execution logic
    """

    name: str = Field(description="Unique tool identifier")
    description: str = Field(description="Tool description for Agent selection")

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with success status and data
        """
        pass

    def validate(self, **kwargs) -> bool:
        """
        Validate input parameters before execution.
        Override in subclasses for custom validation.

        Returns:
            True if valid, raises ValueError if invalid
        """
        return True

    def to_dict(self) -> Dict[str, str]:
        """Convert tool to dictionary for Agent configuration."""
        return {
            "name": self.name,
            "description": self.description
        }
