#!/bin/bash
set -e

python -m prisma migrate deploy

exec "$@"