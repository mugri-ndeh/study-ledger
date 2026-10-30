#!/bin/sh
# Container start: bring the database schema up to date and load the built-in data, then run the server.
set -e
alembic upgrade head
python -m cli bootstrap
exec "$@"
