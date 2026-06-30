"""Dummy required settings so importing app.* doesn't need a real env or DB.

app.config.Settings requires AMF_API_KEY / AMF_DATABASE_URL at import time, and
app.db builds an engine from the URL (lazily — it never connects here). Set both
before any app module is imported during collection.
"""

import os

os.environ.setdefault("AMF_API_KEY", "test-api-key-0123456789")
os.environ.setdefault("AMF_DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
