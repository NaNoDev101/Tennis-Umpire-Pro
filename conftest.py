"""
conftest.py — pytest configuration for Tennis Umpire Pro.

Adds the project root to ``sys.path`` so tests can import engine/theme
modules without installing the package first.
"""

import sys
import os

# Ensure the project root (tennis_umpire_pro/) is on sys.path regardless
# of where pytest is invoked from.
sys.path.insert(0, os.path.dirname(__file__))
