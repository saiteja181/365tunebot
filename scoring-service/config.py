"""
Configuration for Security Scoring Service
Loads settings from environment variables
"""

import os
from dotenv import load_dotenv

load_dotenv()

# SQL Server Configuration
SQL_SERVER = os.getenv("SQL_SERVER", "liclensdbsrv.database.windows.net")
SQL_DATABASE = os.getenv("SQL_DATABASE", "LicLensDev")
SQL_USERNAME = os.getenv("SQL_USERNAME", "liclensadmin")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

# Validate critical environment variables
if not SQL_PASSWORD:
    raise ValueError("SQL_PASSWORD environment variable is required")

# Service Configuration
SERVICE_PORT = int(os.getenv("PORT", 8001))
SERVICE_ENV = os.getenv("ENVIRONMENT", "development")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
