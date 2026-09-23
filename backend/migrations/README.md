# Migrations

For the hackathon the schema is defined in one place — the SQLAlchemy models in
`app/models/` — and applied without hand-written SQL:

```bash
python -m app.db.init_db           # create missing tables
python -m app.db.init_db --reset   # drop + recreate all tables (empty)
python -m simulator.seed           # drop + recreate + load synthetic data + verify
```

There is no incremental migration tool (e.g. Alembic) yet: the database is always
rebuilt from the models plus the deterministic seed, which is what the demo needs.
If we ever have to preserve data across schema changes, add Alembic here and
autogenerate the first revision from `app.models.Base.metadata`.
