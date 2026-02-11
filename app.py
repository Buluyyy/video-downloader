from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import os
import re
import uuid

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

FFMPEG_LOCATION = "/usr/bin"


def sanitize_filename(title):
    title = re.sub(r'[\\/*?:"<>|]', "", title)
    return title[:150]


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/download", methods=["POST"])
def download_video():
    data = request.get_json()
    url = data.get("url")
    format_type = data.get("format", "mp4")

    if not url:
        return jsonify({"success": False, "message": "URL tidak ditemukan"}), 400

    try:
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

        # 🎵 MP3 MODE
        if format_type == "mp3":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            })

        # 🎬 MP4 MODE (PALING STABIL)
        else:
            ydl_opts.update({
                "format": "best",
                "postprocessors": [{
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                }]
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for file in os.listdir(DOWNLOAD_FOLDER):
            if file.startswith(base_filename):
                return jsonify({
                    "success": True,
                    "downloadUrl": f"/downloads/{file}"
                })

        return jsonify({
            "success": False,
            "message": "File tidak ditemukan"
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Gagal: {str(e)}"
        }), 500


@app.route("/downloads/<path:filename>")
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
