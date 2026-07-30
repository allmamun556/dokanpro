from typing import Optional

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from app.core.config import settings
from app.db.tenant_scope import TENANT_SCOPED_MODELS

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_scoped_session(tenant_id: Optional[int]) -> Session:
    """
    A fresh Session with every ORM SELECT for a TENANT_SCOPED_MODELS class
    automatically filtered to tenant_id (no-op when tenant_id is None).
    Shared by both get_db (HTTP, reads tenant_id off request.state) and the
    WebSocket route (no Request object available there, so it can't use
    get_db as a FastAPI dependency — it calls this directly instead).
    """
    db = SessionLocal()
    if tenant_id is not None:
        # NOTE: the lambda below must capture tenant_id via a genuine lexical
        # closure (not a `tid=tenant_id` default-argument trick) — SQLAlchemy's
        # statement cache keys with_loader_criteria lambdas by inspecting their
        # __closure__ cells (track_closure_variables=True, the default). A
        # default-argument value lives in __defaults__, which isn't inspected,
        # so every call was compiling once and then reusing that first
        # tenant_id's cached plan for every other tenant's session.
        @event.listens_for(db, "do_orm_execute")
        def _filter_by_tenant(execute_state):
            for model in TENANT_SCOPED_MODELS:
                execute_state.statement = execute_state.statement.options(
                    with_loader_criteria(
                        model,
                        lambda cls: cls.business_id == tenant_id,
                        include_aliases=True,
                    )
                )
    return db


def get_db(request: Request):
    db = get_scoped_session(getattr(request.state, "business_id", None))
    try:
        yield db
    finally:
        db.close()
