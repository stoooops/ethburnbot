#!/bin/bash

set -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

docker rm -f ethburnbot_lint_isort
docker run \
    -v ${SCRIPT_DIR}:/app \
    --name ethburnbot_lint_isort \
    -t ethburnbot \
    python -m isort /app

docker rm -f ethburnbot_lint_black
docker run \
    -v ${SCRIPT_DIR}:/app \
    --name ethburnbot_lint_black \
    -t ethburnbot \
    python -m black /app

sudo chown -R $USER:$USER ${SCRIPT_DIR}
