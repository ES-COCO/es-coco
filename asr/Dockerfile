FROM python:3.9.14-bullseye

RUN apt-get update && apt-get install -y ffmpeg \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN pip install git+https://github.com/openai/whisper.git
WORKDIR /workspace

ENTRYPOINT ["whisper"]
CMD ["--help"]
