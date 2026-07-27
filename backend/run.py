"""Start the IACI backend server."""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from app.core.config import get_settings
s = get_settings()
print(f"Starting IACI — model: {s.litellm_model} neo4j: {s.neo4j_uri}")

import uvicorn
uvicorn.run("app.main:app", host="0.0.0.0", port=8001)
