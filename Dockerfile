FROM python:3.10

# Install FFmpeg (Video/Audio processing ke liye zaroori hai)
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask port setup
ENV FLASK_APP=app.py
EXPOSE 7860

# Run with Gunicorn on Hugging Face default port
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]