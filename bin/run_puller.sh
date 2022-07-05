#!/bin/bash

set -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO_DIR=$(dirname $SCRIPT_DIR)

make build

docker stop ethburnbot_puller
docker rm -f ethburnbot_puller
docker run \
    -v ${REPO_DIR}:/app \
    --name ethburnbot_puller \
    -t ethburnbot \
    python -m bin.run_puller "${@}"

