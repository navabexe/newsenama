#!/usr/bin/env python3
"""
Entrypoint script for development and management tasks.
"""
from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path

from common.logging.logger import log_info

# === Add 'src' directory to PYTHONPATH ===
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# === Optional: Load environment variables if needed ===
from dotenv import load_dotenv
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

# === Optional: Setup logger if needed early ===

def main():
    log_info("Manage script started.")
    # You can define CLI commands here or route to other runners
    print("Welcome to Marketplace Manager.")
    print("Use this file to run tasks like seeding, testing, etc.")

if __name__ == "__main__":
    main()
