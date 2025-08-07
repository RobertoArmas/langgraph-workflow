## Migrations

Create migrations

```bash
 uv run alembic revision --autogenerate -m "create movies"
```

Run migrations

```bash
uv run alembic upgrade head
```

Rollback migration

```bash
uv run alembic downgrade -1
```
