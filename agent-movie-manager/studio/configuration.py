import os

from dataclasses import dataclass, field, fields
from typing import Any, Optional
from langchain_core.runnables import RunnableConfig
from typing_extensions import Annotated
from pydantic import BaseModel

class Configuration(BaseModel):
    """The configurable fields for the chatbot."""
    user_id: str = "default-user"
    assistant_role: str = (
        "You are a helpful movie theater assistant. You can search for movies, list them, and also search online for movie information."
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f: os.environ.get(f.upper(), configurable.get(f))
            for f in cls.model_fields
        }
        return cls(**{k: v for k, v in values.items() if v})

    class Config:
        arbitrary_types_allowed = True