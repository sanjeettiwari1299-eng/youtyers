FROM python:3.12-slim

# ffmpeg is needed for merging video+audio and for mp3 extraction
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U yt-dlp

WORKDIR /app
COPY server.py .

ENV PORT=9000
EXPOSE 9000
CMD ["python", "-u", "server.py"]
