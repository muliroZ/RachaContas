from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./contas.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _ativar_fks(conn, _):
    conn.execute("PRAGMA foreign_keys=on")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
