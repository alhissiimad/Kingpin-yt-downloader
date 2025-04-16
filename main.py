import os
import glob
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL
import subprocess


BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")

app = Client("yt_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)


def clean_downloads():
    for f in glob.glob("downloads/*"):
        os.remove(f)


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:.2f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.2f} Y{suffix}"


def get_video_formats(url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        valid = []
        for f in formats:
            if not f.get("vcodec") or "audio only" in f.get("format_note", ""):
                continue
            if f.get("filesize") and f["filesize"] > 50 * 1024 * 1024:
                continue
            if not f.get("acodec") or f.get("acodec") == "none":
                continue
            label = f"{f['format_note']} | {sizeof_fmt(f['filesize'])}"
            valid.append((label, f["format_id"]))
        return valid


@app.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply("👋 Send me a YouTube video link.")


@app.on_message(filters.regex(r"https?://.*(youtube.com|youtu.be)/"))
async def link_handler(client, message):
    url = message.text.strip()
    await message.reply("🔍 Processing the video... Please wait.")

    try:
        formats = get_video_formats(url)
        if not formats:
            await message.reply("❌ No valid formats with sound found.")
            return

        buttons = [
            [InlineKeyboardButton(text=label, callback_data=f"{format_id}|{url}")]
            for label, format_id in formats
        ]

        await message.reply(
            "🎬 Choose a quality to download:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        await message.reply(f"❌ Failed to process link.\n\n{e}")


@app.on_callback_query()
async def handle_button(client, callback):
    await callback.answer()
    await callback.message.reply("📥 Downloading video...")

    clean_downloads()
    fmt, url = callback.data.split("|")

    try:
        ydl_opts = {
            "format": fmt,
            "outtmpl": "downloads/input.mp4",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Re-encode to ensure iPhone/web compatibility (force H.264 + AAC)
        output_file = "downloads/output_ios.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", "downloads/input.mp4",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_file,
        ]
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if process.returncode != 0:
            raise Exception("FFmpeg failed:", process.stderr.decode())

        await callback.message.reply_video(
            video=output_file,
            caption="✅ Here is your video!",
        )

    except Exception as e:
        await callback.message.reply(f"❌ Failed to download.\n\n**Reason:**\n{e}")

    finally:
        clean_downloads()


if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    print("Bot is running...")
    app.run()
