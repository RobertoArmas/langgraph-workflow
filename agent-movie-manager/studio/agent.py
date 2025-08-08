from __future__ import annotations

from langchain_core.messages import SystemMessage, AIMessage, ChatMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore

"""LangGraph workflow for a conversational "Movie Assistant".

*Updated to plug in Roberto’s **real** tools:*

- **list_movies** → already implemented in `common.repositories.movie_repository` (returns `list[Movie]`).
- **insert_movie** → upsert helper that **creates or updates** a row via the same repository.

The rest of the workflow (search‑online, build dict, ask‑user, etc.) stays the same.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict, List, Literal, Union

from langgraph.graph import START, END, StateGraph, MessagesState

# ---------------------------------------------------------------------------
# REAL tools ----------------------------------------------------------------
# ---------------------------------------------------------------------------

from common.repositories.movie_repository import MovieRepository
from common.models.movie import Movie

def list_movies() -> list[str]:
    """List all movies."""
    repo = MovieRepository()
    # map to str for better readability
    return [str(m) for m in repo.all()]  # Convert to str for better readability

def search_movies(query: str | None = None) -> list[Movie]:
    """Search for movies matching the query."""
    repo = MovieRepository()
    if query:
        # assume repository supports a text search; fall back to returning all
        if hasattr(repo, "search_by_text"):
            return repo.search_by_text(query)
    return repo.all()

def delete_movie_by_id(movie_id: int) -> bool:
    """Delete a movie by ID."""
    repo = MovieRepository()
    repo.delete(movie_id)
    return True

def update_movie(movie: Dict[str, Any]) -> str:
    """Update an existing movie."""
    repo = MovieRepository()
    current_movie = repo.get(movie["id"])
    if current_movie:
        for key, value in movie.items():
            setattr(current_movie, key, value)
        repo.save(current_movie)
    return str(current_movie)

def update_price(movie_id: int, new_price: float) -> str:
    """Update the price of a movie."""
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
    print(f"Insert movie with data: {movie_data}")
    repo = MovieRepository()
    name = movie_data.get("name")
    if name:
        if hasattr(repo, "get_by_name"):
            existing = repo.get_by_name(name)
        else:
            existing = None
    else:
        existing = None


    repo.create(movie_data)
    


# ---------------------------------------------------------------------------
# Stub tool (still needs real API) -----------------------------------------
# ---------------------------------------------------------------------------

def search_movie_online(title: str) -> dict:
    """Call OMDb/TMDB/etc. Replace with real HTTP call."""
    return {
        "name": title,
        "description": f"Description for {title}",
        "release_year": 2020,
        "rating": 7.5,
        "is_imax": False,
        "price": 10.0,
    }


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

tools = [list_movies, insert_movie, delete_movie_by_id, update_movie, search_movies, update_price]
llm = ChatOpenAI(
    model="gpt-4o",
)
llm_with_tools = llm.bind_tools(tools)

# ---------------------------------------------------------------------------
# State object --------------------------------------------------------------
# ---------------------------------------------------------------------------
from typing import Annotated

@dataclass
class MovieState(MessagesState):
    user_input: Annotated[str, "User's input text"]
    movies_from_db: Optional[list[Movie]]
    online_info: Optional[dict]
    movie_obj: Optional[Movie]
    approved: Optional[bool]
    db_row_id: Optional[int]

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

    state["messages"] = [llm_with_tools.invoke([sys_message] + state["messages"])]

    return state

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
    new_memory = llm_with_tools.invoke([SystemMessage(content=system_msg)]+state['messages'])

    # Overwrite the existing memory in the store 
    key = "user_memory"
    store.put(namespace, key, {"memory": new_memory.content})


def show_options(state: MovieState) -> MovieState:
    """Show available options to the user."""

    state["messages"].append(
        ChatMessage(
            content="What would you like to do? You can search for a movie, list all movies, or insert a new movie.",   
            role="assistant"
        )
    )
    return state


def needs_search(state: MovieState) -> bool:
    return state.get("online_info") is None


def run_search(state: MovieState) -> MovieState:
    if not state.get("user_input"):
        return state
    info = search_movie_online(state["user_input"])
    state["online_info"] = info
    return state


def build_movie_obj(state: MovieState) -> MovieState:
    info = state.get("online_info") or {}
    movie = Movie(**info) if isinstance(info, dict) else info
    state["movie_obj"] = movie
    return state


def confirm_with_user(state: MovieState) -> MovieState:
    # TODO integrate real chat. For now auto‑approve
    state["approved"] = True
    return state


def insert_db(state: MovieState) -> MovieState:
    """Insert the movie into the database."""
    if state["movie_obj"] is None:
        raise ValueError("No movie object to insert into the database.")
    movie = state["movie_obj"]
    # Always convert to dict for insert_movie
    if isinstance(movie, Movie):
        movie_data = movie.__dict__
    else:
        movie_data = dict(movie)
    row_id = insert_movie(movie_data)
    state["db_row_id"] = row_id
    return state


# ---------------------------------------------------------------------------
# Edge Conditions ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def smart_condition(
    state: Union[list[Any], dict[str, Any]],
    messages_key: str = "messages",
) -> Literal["tools", "write_memory", END]:
    next_state = tools_condition(state, messages_key)
    if next_state == "tools":
        return "tools"
    # last message if last message if tool call then return END
    if isinstance(state, dict) and state.get("messages"):
            last_message = state["messages"][-1]
            if hasattr(last_message, "additional_kwargs") and hasattr(last_message.additional_kwargs, "tool_calls") and len(last_message.additional_kwargs["tool_calls"]) > 0:
                return END
    return "write_memory"

def is_approved(state: MovieState) -> Literal["insert", "search"]:
    if( state.get("approved") is None ):
        return "search"
    return "insert"

# ---------------------------------------------------------------------------
# Build graph ---------------------------------------------------------------
# ---------------------------------------------------------------------------
import configuration

workflow = StateGraph(MovieState, config_schema=configuration.Configuration)

# Define a new graph
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
