from yt_dlp import YoutubeDL


def get_merged_formats(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        video_formats = []
        audio_formats = []

        for f in info['formats']:
            if f.get('vcodec') != 'none' and f.get('acodec') == 'none' and f.get('filesize'):
                video_formats.append(f)
            elif f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('filesize'):
                audio_formats.append(f)

        # Pick best audio (highest bitrate)
        best_audio = max(audio_formats, key=lambda a: a.get('abr', 0), default=None)

        results = []
        for v in video_formats:
            total_size = v['filesize'] + (best_audio['filesize'] if best_audio else 0)
            results.append({
                "format_id": f"{v['format_id']}+{best_audio['format_id']}" if best_audio else v["format_id"],
                "quality": f"{v.get('format_note') or str(v.get('height'))}p",
                "filesize": total_size,
                "ext": v.get('ext')
            })

        return results
