#!/bin/bash

set -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO_DIR=$(dirname $SCRIPT_DIR)

docker stop ethburnbot_tweeter
docker rm -f ethburnbot_tweeter
docker run \
    -v ${REPO_DIR}:/app \
    --name ethburnbot_tweeter \
    -t ethburnbot \
    python -m bin.run_tweeter "${@}"

