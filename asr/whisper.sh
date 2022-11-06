#!/bin/bash
set -euo pipefail

dir=$(readlink -m "$(dirname "$1")")
fname=$(basename "$1")

docker build -t whisper . &&
	docker run --rm -it --gpus all \
		--shm-size=10.24gb \
		-e TERM=xterm-256color \
		-v "${WHISPER_CACHE_DIR}:/root/.cache/whisper/" \
		-v "${dir}:/workspace" \
		whisper "$fname" "${@:2}"
