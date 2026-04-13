import os
import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

# Browser simulation to avoid blocks
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/fetch', methods=['GET'])
def fetch_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Link missing"}), 400

    try:
        # Expert YDL Config: Progressive formats only (Video+Audio merged)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]/best',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats_list = []

            for f in info.get('formats', []):
                # Only grab formats that have both video and audio to ensure gallery compatibility
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                    res = f.get('height')
                    if res:
                        formats_list.append({
                            "quality": f"{res}p",
                            "url": f.get('url')
                        })

            # Filter for unique resolutions
            unique_formats = {f['quality']: f for f in formats_list}.values()

            # Find a separate audio stream for MP3 conversion
            audio_url = None
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_url = f.get('url')
                    break

            return jsonify({
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "uploader": info.get('uploader', 'Saqib Pro'),
                "duration": info.get('duration_string', '0:00'),
                "formats": sorted(unique_formats, key=lambda x: int(x['quality'][:-1]), reverse=True),
                "audio_url": audio_url or info.get('url')
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/download')
def download_proxy():
    file_url = request.args.get('url')
    file_name = request.args.get('name', 'MediaFetch_Video')
    file_type = request.args.get('type', 'video')

    # Clean filename for Android
    clean_name = "".join([c for c in file_name if c.isalnum() or c in (' ', '-', '_')]).strip()
    extension = ".mp3" if file_type == "audio" else ".mp4"

    try:
        # Stream the file through the server to bypass YouTube blocks and 0-byte errors
        r = requests.get(file_url, stream=True, headers=HEADERS, timeout=300)

        @stream_with_context
        def generate():
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    yield chunk

        return Response(
            generate(),
            content_type=r.headers.get('Content-Type'),
            headers={
                "Content-Disposition": f"attachment; filename=\"{clean_name}{extension}\"",
                "Content-Length": r.headers.get('Content-Length')
            }
        )
    except Exception as e:
        return str(e), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)