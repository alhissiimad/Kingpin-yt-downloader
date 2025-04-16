from yt_dlp import YoutubeDL


def get_muxed_formats(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        formats = []
        for f in info['formats']:
            if (f.get("vcodec") != "none" and f.get("acodec") != "none"
                    and f.get("filesize")
                    and f.get("ext") in ["mp4", "mkv", "webm"]):
                formats.append({
                    "format_id":
                    f["format_id"],
                    "quality":
                    f.get("format_note") or f.get("height"),
                    "filesize":
                    f["filesize"],
                    "ext":
                    f["ext"]
                })

        return formats
