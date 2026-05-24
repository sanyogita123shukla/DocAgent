import json
from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel
from langchain_core.tools import BaseTool


class SkillInput(BaseModel):
    """Base input schema. All skills extend this."""
    file_path: str


class AbstractSkill(BaseTool, ABC):
    """
    The core abstraction. Every document skill inherits from this.
    
    Subclasses MUST define:
      - name: str
      - description: str  (this is the LLM's prompt for tool selection)
      - args_schema: Type[BaseModel]
      - _execute(self, **kwargs) -> dict
    """
    
    @abstractmethod
    def _execute(self, *args, **kwargs) -> dict[str, Any]:
        """Core logic. Returns structured JSON."""
        pass

    def _run(self, *args, **kwargs) -> str:
        """LangGraph calls this. We wrap _execute with error handling."""
        try:
            result = self._execute(*args, **kwargs)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "skill": self.name})
