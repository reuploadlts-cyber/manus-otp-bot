#!/usr/bin/env python3
"""Entry point for running the OTP Forwarder Bot."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
