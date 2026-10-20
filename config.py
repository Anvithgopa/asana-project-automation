"""
Centralized Configuration Loader for Asana Automation Toolkit.
Loads environment variables safely without exposing hardcoded credentials.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Asana Authentication & Workspace Settings
ASANA_ACCESS_TOKEN = os.getenv("ASANA_ACCESS_TOKEN", "")
WORKSPACE_GID = os.getenv("ASANA_WORKSPACE_GID", "")

# Directory Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
LOG_DIR = os.getenv("LOG_DIR", os.path.join(BASE_DIR, "logs"))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
