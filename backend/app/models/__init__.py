"""Central import point so every model is registered on SQLModel.metadata
before create_db_and_tables() runs — SQLModel only creates tables for models
that have actually been imported into the process. Import this module (not
individual model files) wherever table creation happens.

Caught the hard way in Step 4: `main.py` only imported `app.models.user`
(transitively, via the users router) and `create_all()` silently created
ONLY the users table — search_sessions/search_messages/memory_notes would
have been missing until whichever later step happened to import them first,
a bug that wouldn't have surfaced until Step 5/6 hit a live "no such table"
error. See AgentGuide/05_PROJECT_STATE.md Step 4 notes.
"""

from app.models.memory import *  # noqa: F401,F403
from app.models.search import *  # noqa: F401,F403
from app.models.user import *  # noqa: F401,F403
