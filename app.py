from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import os
import re
import uuid
import requests

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

FFMPEG_LOCATION = "/usr/bin"  # Railway / Linux path


def sanitize_filename(title):
    """Hapus karakter illegal untuk filename"""
    title = re.sub(r'[\\/*?:"<>|]', "", title)
    return title[:150]


def get_spotify_metadata(url):
    """Ambil judul lagu dari Spotify track link"""
    match = re.search(r"track/([a-zA-Z0-9]+)", url)
    if not match:
        return None
    track_id = match.group(1)
    oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
    response = requests.get(oembed_url)
    if response.status_code != 200:
        return None
    data = response.json()
    return data.get("title")


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/download", methods=["POST"])
def download_video():
    data = request.get_json()
    url = data.get("url")
    format_type = data.get("format", "mp4")
    platform = data.get("platform", "youtube")

    if not url:
        return jsonify({"success": False, "message": "URL tidak ditemukan"}), 400

    try:
        # 🎵 Spotify Mode: ambil judul + search YouTube
        if platform.lower() == "spotify":
            spotify_title = get_spotify_metadata(url)
            if not spotify_title:
                return jsonify({"success": False, "message": "Gagal ambil data Spotify"}), 400
            url = f"ytsearch1:{spotify_title}"
            format_type = "mp3"  # Paksa MP3

        # Ambil judul dulu
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "cookiefile": "cookies.txt"
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = info.get("title", "video")

        title = sanitize_filename(raw_title)
        unique_id = str(uuid.uuid4())[:8]
        base_filename = f"{title}_{unique_id}"

        output_template = os.path.join(
            DOWNLOAD_FOLDER,
            f"{base_filename}.%(ext)s"
        )

        ydl_opts = {
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "ffmpeg_location": FFMPEG_LOCATION,
            "cookiefile": "cookies.txt"
        }

        if format_type.lower() == "mp3":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            })
        else:
            ydl_opts.update({
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                "merge_output_format": "mp4"
            })

        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Cari file hasil download
        for file in os.listdir(DOWNLOAD_FOLDER):
            if file.startswith(base_filename):
                return jsonify({
                    "success": True,
                    "downloadUrl": f"/downloads/{file}"
                })

        return jsonify({"success": False, "message": "File tidak ditemukan"}), 500

    except Exception as e:
        return jsonify({"success": False, "message": f"Gagal: {str(e)}"}), 500


@app.route("/downloads/<path:filename>")
def serve_file(filename):
    """Serve file safely"""
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.isfile(file_path):
        return jsonify({"success": False, "message": "File tidak ditemukan"}), 404
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
