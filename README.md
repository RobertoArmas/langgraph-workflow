# LangGraph Agent Movie Manager

## Description

LangGraph Agent Movie Manager is a Python-based application designed to manage a movie database using modern agent-based and workflow-driven approaches. It leverages SQLAlchemy for ORM, Alembic for migrations, and a modular repository pattern for clean data access. The project supports full CRUD operations for movies, including search functionality, and is structured for extensibility and maintainability. It is suitable for learning, prototyping, or as a foundation for more advanced movie management systems.

## Architecture

The project is organized into several key folders:

- **agent-movie-manager/**: Contains the main agent application, designed to connect to a Microsoft SQL Server database. This is where the agent logic, workflows, and studio interface are implemented.

- **seeds/**: Contains scripts for seeding the database with initial data.

- **migrations/**: Contains the Alembic migration project for managing database schema migrations.

- **common/**: Houses general application logic, including database connection utilities, models, and repository classes for data access and business logic.

This modular structure separates concerns, making the codebase easier to maintain and extend. The agent interacts with the database through the repository pattern, migrations ensure the database schema is up to date, and seeds provide initial data for development or testing.

## Configuration

To configure the project environment variables:

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Open the newly created `.env` file and fill in the required environment variables, such as database connection strings and any API keys needed for the application.

Example variables:

```
OPENAI_API_KEY=

DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=1433
DB_NAME="MovieTheater"


LANGSMITH_API_KEY=
LANGSMITH_TRACING_V2=
LANGSMITH_PROJECT=
```

### Install UV and Sync Env

To set up the Python environment using [uv](https://github.com/astral-sh/uv):

1. Install uv (if not already installed):

   ```bash
   pip install uv
   ```

2. Sync your environment with the project dependencies:

   ```bash
   uv sync
   ```

This will install all dependencies specified in `pyproject.toml` and `uv.lock`.

### Run the Application Migrations

Run migrations

```bash
uv run alembic upgrade head
```

Rollback migration (in case of migration rollback needed)

```bash
uv run alembic downgrade -1
```

### Run LangGraph Studio

To start the LangGraph Studio for interactive development and testing:

1. Change to the studio directory:

   ```bash
   cd agent-movie-manager/studio
   ```

2. Start the LangGraph Studio development server:

   ```bash
   uv run langgraph dev
   ```

## License

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)

This project is built for educational purposes as part of the Maestría de Inteligencia Aplicada at Universidad de las Américas (UDLA). It is intended for learning, research, and academic use only, and was not designed for production environments.

Additionally, the code is provided under the terms of the [MIT License](LICENSE), allowing open source use, modification, and distribution.
