#!/bin/bash

set -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

docker stop ethburnbot_tweeter
docker rm -f ethburnbot_tweeter
docker run \
    -v ${SCRIPT_DIR}:/app \
    --name ethburnbot_tweeter \
    -t ethburnbot \
    python -m run_tweeter "${@}"
