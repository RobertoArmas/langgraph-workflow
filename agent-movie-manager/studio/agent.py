from __future__ import annotations
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Union
from langgraph.graph import START, StateGraph, MessagesState
from typing import Annotated
from common.repositories.movie_repository import MovieRepository
from common.models.movie import Movie
import configuration

# ---------------------------------------------------------------------------
# PROMPTS -------------------------------------------------------------------
# ---------------------------------------------------------------------------

CREATE_MEMORY_INSTRUCTION = """"You are collecting information about the user to personalize your responses.

CURRENT USER INFORMATION:
{memory}

INSTRUCTIONS:
1. Review the chat history below carefully
2. Identify new information about the user, such as:
   - Personal details (name, location)
   - Preferences (likes, dislikes)
   - Interests and hobbies
   - Past experiences
   - Goals or future plans
3. Merge any new information with existing memory
4. Format the memory as a clear, bulleted list
5. If new information conflicts with existing memory, keep the most recent version

Remember: Only include factual information directly stated by the user. Do not make assumptions or inferences.

Based on the chat history below, please update the user information:"""

# ---------------------------------------------------------------------------
# REAL tools ----------------------------------------------------------------
# ---------------------------------------------------------------------------

def list_movies() -> list[str]:
    """List all movies.
    
    Returns:
        A list of movies.
    """
    repo = MovieRepository()
    # map to str for better readability
    return [str(m) for m in repo.all()]  # Convert to str for better readability

def search_movies(query: str | None = None) -> list[Movie]:
    """Search for movies matching the query.
    
    Arguments:
        query: The search query string.
    
    Returns:
        A list of movies matching the query.
    """
    repo = MovieRepository()
    if query:
        # assume repository supports a text search; fall back to returning all
        if hasattr(repo, "search_by_text"):
            return repo.search_by_text(query)
    return repo.all()

def delete_movie_by_id(movie_id: int) -> bool:
    """Delete a movie by ID.
    
    Arguments:
        movie_id: The ID of the movie to delete.
    Returns:
        True if the movie was deleted, False otherwise.
    """
    repo = MovieRepository()
    repo.delete(movie_id)
    return True

def update_movie(movie: Dict[str, Any]) -> str:
    """Update an existing movie.
    
    Arguments:
        movie: A dictionary containing the updated movie data.
    """
    repo = MovieRepository()
    current_movie = repo.get(movie["id"])
    if current_movie:
        for key, value in movie.items():
            setattr(current_movie, key, value)
        repo.save(current_movie)
    return str(current_movie)

def update_price(movie_id: int, new_price: float) -> str:
    """Update the price of a movie.
    
    Arguments:
        movie_id: The ID of the movie to update.
        new_price: The new price to set.
    Returns:
        The updated movie as a string.
    """
    repo = MovieRepository()
    movie = repo.get(movie_id)
    if movie:
        movie.price = new_price
        repo.save(movie)
    return str(movie)

def insert_movie(movie_data: dict) -> int:
    """Insert a movie.

    Arguments:
        movie_data: Movie data as a dict.

    Returns:
        The ID of the inserted movie.
    """
    repo = MovieRepository()
    id = repo.create(movie_data)
    return id

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

tools = [list_movies, insert_movie, delete_movie_by_id, update_movie, search_movies, update_price]
llm = ChatOpenAI(
    model="gpt-4o",
)
model = llm.bind_tools(tools)

# ---------------------------------------------------------------------------
# State object --------------------------------------------------------------
# ---------------------------------------------------------------------------

@dataclass
class MovieState(MessagesState):
    user_input: Annotated[Optional[str], "User's input text"]

# ---------------------------------------------------------------------------
# Nodes ---------------------------------------------------------------------
# ---------------------------------------------------------------------------

def assistant(state: MovieState, config: RunnableConfig, store: BaseStore) -> MovieState:
    """Determine intent from user_input and orchestrate flow."""
    # Get configuration
    configurable = configuration.Configuration.from_runnable_config(config)
    
    # Get the user ID from the config
    user_id = configurable.user_id

    # Retrieve memory from the store
    namespace = ("memory", user_id)
    key = "user_memory"
    existing_memory = store.get(namespace, key)

    # Extract the memory
    if existing_memory:
        # Value is a dictionary with a memory key
        existing_memory_content = existing_memory.value.get('memory')
    else:
        existing_memory_content = "No existing memory found."

    # Chatbot instruction
    MODEL_SYSTEM_MESSAGE = """You are a helpful assistant with memory that provides information about movies. 
    If you have memory for this user, use it to personalize your responses.
    You can search for movies, list them, and also search online for movie information.
    Here is the memory (it may be empty): {memory}"""

    sys_message = SystemMessage(
        content=MODEL_SYSTEM_MESSAGE.format(memory=existing_memory_content)
    ) 

    state["messages"] = [model.invoke([sys_message] + state["messages"])] # type: ignore

    return state

def write_memory(state: MovieState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and save a memory to the store."""
    if isinstance(state, dict) and state.get("messages"):
        last_message = state["messages"][-1]
        if hasattr(last_message, "additional_kwargs") and hasattr(last_message.additional_kwargs, "tool_calls") and len(last_message.additional_kwargs["tool_calls"]) > 0:
            return state
    # Get configuration
    configurable = configuration.Configuration.from_runnable_config(config)

    # Get the user ID from the config
    user_id = configurable.user_id

    # Retrieve existing memory from the store
    namespace = ("memory", user_id)
    existing_memory = store.get(namespace, "user_memory")

    # Extract the memory
    if existing_memory:
        # Value is a dictionary with a memory key
        existing_memory_content = existing_memory.value.get('memory')
    else:
        existing_memory_content = "No existing memory found."
        
    # Format the memory in the system prompt
    system_msg = CREATE_MEMORY_INSTRUCTION.format(memory=existing_memory_content)
    new_memory = model.invoke([SystemMessage(content=system_msg)]+state['messages'])

    # Overwrite the existing memory in the store 
    key = "user_memory"
    store.put(namespace, key, {"memory": new_memory.content})


# ---------------------------------------------------------------------------
# Edge Conditions ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def smart_condition(
    state: Union[list[Any], dict[str, Any]],
    messages_key: str = "messages",
) -> Literal["tools", "write_memory", "__end__"]:
    next_state = tools_condition(state, messages_key)
    if next_state == "tools":
        return "tools"
    # last message if last message if tool call then return END
    if isinstance(state, dict) and state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, "additional_kwargs") and hasattr(last_message.additional_kwargs, "tool_calls") and len(last_message.additional_kwargs["tool_calls"]) > 0:
                return "__end__"
    return "write_memory"

def is_approved(state: MovieState) -> Literal["insert", "search"]:
    if( state.get("approved") is None ):
        return "search"
    return "insert"

# ---------------------------------------------------------------------------
# Build graph ---------------------------------------------------------------
# ---------------------------------------------------------------------------

# Define a new graph
workflow = StateGraph(MovieState, context_schema=configuration.Configuration)

# Define the nodes that will be used in the graph
workflow.add_node("assistant", assistant)
workflow.add_node("write_memory", write_memory)
workflow.add_node("tools", ToolNode(tools))

# Set the entrypoint as conversation
# Define entrypoint: START ➜ assistant
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges("assistant", smart_condition)
workflow.add_edge("tools", "assistant")

# Compile
graph = workflow.compile()
