from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import os
import re

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ✅ GANTI jika lokasi ffmpeg berbeda
FFMPEG_LOCATION = r"C:\ffmpeg\bin"

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)


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
        # Ambil info video
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = info.get("title", "video")

        title = sanitize_filename(raw_title)
        output_template = os.path.join(DOWNLOAD_FOLDER, f"{title}.%(ext)s")

        ydl_opts = {
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "ffmpeg_location": FFMPEG_LOCATION
        }

        # 🎵 MODE MP3
        if format_type == "mp3":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            })

        # 🎬 MODE MP4 (DIPAKSA MP4, BUKAN WEBM)
        else:
            ydl_opts.update({
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                "merge_output_format": "mp4"
            })

        # 🔥 Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 🔎 Cari file hasil download
        for file in os.listdir(DOWNLOAD_FOLDER):
            if file.startswith(title):
                return jsonify({
                    "success": True,
                    "downloadUrl": f"/downloads/{file}"
                })

        return jsonify({
            "success": False,
            "message": "File tidak ditemukan setelah download"
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
    app.run(debug=True)