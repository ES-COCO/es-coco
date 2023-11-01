#! /usr/bin/env bash
set -euo pipefail

input_path="$2"
wav_path="${input_path%.*}.wav"
out_path="${input_path%.*}"

ffmpeg -i "$input_path" -ar 16000 -ac 1 -c:a pcm_s16le "$wav_path" \
  && whisper-cpp \
    --language auto \
    --model "$1" \
    --output-file "$out_path" \
    --processors 4 \
    --output-csv "$wav_path" \
  && rm -f "$wav_path"
