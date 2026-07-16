"""VeriGate - Flask + MongoDB Backend Project.

A verification and MIS (Management Information System) backend application.
"""

from .app import create_app, app

__all__ = ['create_app', 'app']