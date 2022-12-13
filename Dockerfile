FROM python:3.9-slim
WORKDIR /src
COPY requirements.txt requirements.txt
RUN pip install --user --no-warn-script-location -r requirements.txt
RUN apt-get update && apt-get install -y git
RUN python -m pip install git+https://github.com/openai/whisper.git
RUN apt update
RUN apt install ffmpeg -y
CMD ["python", "app.py"]