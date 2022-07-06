#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail
set -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO_DIR=$(dirname $SCRIPT_DIR)

docker rm -f ethburnbot_lint_isort
docker run \
    -v ${REPO_DIR}:/app \
    --name ethburnbot_lint_isort \
    --user $(id -u):$(id -g) \
    -t ethburnbot \
    python -m isort --ignore-whitespace /app

docker rm -f ethburnbot_lint_black
docker run \
    -v ${REPO_DIR}:/app \
    --name ethburnbot_lint_black \
    --user $(id -u):$(id -g) \
    -t ethburnbot \
    python -m black /app
