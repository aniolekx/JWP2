docker run -it --device /dev/snd:/dev/snd  --runtime nvidia --gpus all  -v /home/krzysztof/projects/local-talking-llm:/app -w /app  arm64v8/python:3.10-slim bash
