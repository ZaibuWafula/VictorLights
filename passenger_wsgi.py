"""
passenger_wsgi.py — the entry point file DirectAdmin's (and cPanel's)
"Setup Python App" feature looks for. It's built on Phusion Passenger,
which expects a WSGI application object named `application`.

FastAPI is ASGI, not WSGI, so this file adapts one to the other using
a2wsgi. No other file in the project needs to change for this hosting path —
Dockerfile/railway.json/deploy/ are for the other hosting options and are
simply unused here.
"""
import sys
import os

# Make sure the app package is importable regardless of Passenger's cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2wsgi import ASGIMiddleware
from app.main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
