"""MongoDB connection management for VeriGate.

Implements a singleton MongoClient per Flask application as required by
CLAUDE.md (a single long-lived client with internal connection pooling is the
recommended PyMongo pattern). The client and database handle are attached to the
application object and exposed through module-level accessors so repositories
can reach the database without re-creating the client.
"""

from typing import Optional

from flask import Flask, current_app
from pymongo import MongoClient
from pymongo.database import Database


def init_mongo(app: Flask) -> None:
    """Initialise a singleton MongoClient and bind it to the Flask app.

    Args:
        app: The Flask application whose config provides MONGO_URI and
            DATABASE_NAME.
    """
    client = MongoClient(app.config["MONGO_URI"])
    app.extensions["mongo_client"] = client
    app.extensions["mongo_db"] = client[app.config["DATABASE_NAME"]]


def get_client() -> MongoClient:
    """Return the active MongoClient from the current Flask app."""
    client: Optional[MongoClient] = current_app.extensions.get("mongo_client")
    if client is None:
        raise RuntimeError("MongoDB client is not initialised. Call init_mongo(app).")
    return client


def get_db() -> Database:
    """Return the active Database handle from the current Flask app."""
    db: Optional[Database] = current_app.extensions.get("mongo_db")
    if db is None:
        raise RuntimeError("MongoDB database is not initialised. Call init_mongo(app).")
    return db
