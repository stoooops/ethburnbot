#!/bin/bash

set -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

docker stop ethburnbot_puller
docker rm -f ethburnbot_puller
docker run \
    -v ${SCRIPT_DIR}:/app \
    --name ethburnbot_puller \
    -t ethburnbot \
    python -m run_puller "${@}"
