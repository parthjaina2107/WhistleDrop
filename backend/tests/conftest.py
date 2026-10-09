import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Route test runs to an isolated test database so whistledrop.db is never polluted
test_db_path = os.path.join(backend_dir, "test_whistledrop.db")
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.replace(os.sep, '/')}"

from app.database import engine, Base, SessionLocal
from app.auth import seed_default_moderator

# Ensure tables and default moderator exist in test DB
Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    seed_default_moderator(db)
finally:
    db.close()
