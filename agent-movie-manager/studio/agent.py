from __future__ import annotations

from langchain_core.messages import SystemMessage, AIMessage, ChatMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import tools_condition, ToolNode
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

def insert_movie(movie_data: Dict[str, Any]) -> int:
    """Insert a movie.

    Strategy:
    1. Look up by *name*.
    2. If exists → update fields & save.
    3. Else → create a new row.
    Returns the DB primary‑key id.
    """
    repo = MovieRepository()
    name = movie_data.get("name")
    if name:
        if hasattr(repo, "get_by_name"):
            existing = repo.get_by_name(name)
        else:
            existing = None
    else:
        existing = None

    if existing:
        for k, v in movie_data.items():
            setattr(existing, k, v)
        if hasattr(repo, "save"):
            repo.save(existing)
        else:
            raise AttributeError("MovieRepository lacks a 'save' method for update.")
        return existing.id

    # --- create path ---
    movie = Movie(**movie_data)
    if hasattr(repo, "create"):
        repo.create(movie)
    elif hasattr(repo, "save"):
        repo.save(movie)
    else:
        raise AttributeError("MovieRepository lacks 'create' or 'save'.")
    return movie.id


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

def assistant(state: MovieState) -> MovieState:
    """Determine intent from user_input and orchestrate flow."""
    sys_message = SystemMessage(
        content="You are a helpful movie assistant. "
                "You can search for movies, list them, and also search online for movie information."
    )   
    state["messages"] = [llm_with_tools.invoke([sys_message] + state["messages"])]

    # Human in the loop for get user input
    if not state.get("user_input"):
        # If no user input, return the state to wait for it
        return state

    return state

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
    if not isinstance(movie, Movie):
        movie = Movie(**movie)
    row_id = insert_movie(movie.__dict__)
    state["db_row_id"] = row_id
    return state


# ---------------------------------------------------------------------------
# Edge Conditions ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def smart_condition(
    state: Union[list[Any], dict[str, Any]],
    messages_key: str = "messages",
) -> Literal["tools", END]:
    next_state = tools_condition(state, messages_key)
    if next_state == "tools":
        return "tools"
    
    return END

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
assistant_node = workflow.add_node("assistant", assistant)
search_node    = workflow.add_node("search", run_search)
build_node     = workflow.add_node("build", build_movie_obj)
confirm_node   = workflow.add_node("confirm", confirm_with_user)
insert_node    = workflow.add_node("insert", insert_db)

workflow.add_node("tools", ToolNode(tools))

# Set the entrypoint as conversation
# Define entrypoint: START ➜ assistant
workflow.add_edge(START, "assistant")

workflow.add_conditional_edges("assistant", smart_condition)
workflow.add_edge("tools", "assistant")
workflow.add_edge("search", "build")
workflow.add_edge("build", "confirm")



workflow.add_conditional_edges("confirm", is_approved)

workflow.add_edge("insert", END)


# Compile
graph = workflow.compile()

