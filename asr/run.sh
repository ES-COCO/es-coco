#! /usr/bin/env bash

current_dir=$(dirname "$(greadlink -f -- "$0")")
model_name="large"
model_path="${current_dir}/ggml-${model_name}"
model_path="${current_dir}/ggml-${model_name}"
coreml_model_path="models/ggml-${model_name}-encoder.mlmodelc"

# Download the model if it is not downloaded already
if [[ ! -f "$model_path" ]]; then
	whisper-cpp-download-ggml-model "${model_name}"
fi

if [[ "$(uname -sm)" == "Darwin arm64" ]] && [[ ! -f "$coreml_model_path" ]]; then
	# create coreml model
	echo "hi!"
fi
exit 1

fname="$(greadlink -f -- "data/audio/que-pasa-midwest/que-pasa-midwest_1_1_pulque-en-america.mp3")"
outfile="${fname/.mp3/.csv}"

# Convert to .wav
ffmpeg -i "$fname" -ar 16000 -ac 1 -c:a pcm_s16le curfile.wav
# Run ASR
whisper-cpp \
	--model ggml-large.bin \
	--language auto \
	--file curfile.wav \
	--output-csv \
	--output-file "${outfile}"
