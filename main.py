import os
import glob
import subprocess
import shutil
import time

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from downloader import get_merged_formats

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("yt_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

MAX_SIZE_MB = 50

def readable_size(size_bytes):
    mb = size_bytes / (1024 * 1024)
    return f"{mb:.2f} MB"

def reencode_video(input_path: str) -> str:
    os.makedirs("downloads", exist_ok=True)

    safe_input = "downloads/input_safe.mp4"
    output_path = "downloads/output_ios.mp4"

    try:
        shutil.copy(input_path, safe_input)
    except Exception as e:
        raise Exception(f"❌ Failed to copy input: {e}")

    if not os.path.exists(safe_input):
        raise Exception("❌ input_safe.mp4 missing after copy.")

    command = [
        "ffmpeg",
        "-y",  # overwrite without asking
        "-i", safe_input,
        "-vf", "scale='min(1920,iw)':-2",  # ⬅️ Resize down if >1080p (safe for iPhones)
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        completed = subprocess.run(command, capture_output=True, check=True, text=True)
        print("✅ FFmpeg output:\n", completed.stdout)
    except subprocess.CalledProcessError as e:
        raise Exception(f"❌ FFmpeg crashed:\n{e.stderr or e.output}")

    if not os.path.exists(output_path):
        raise Exception("❌ Output file missing after encoding.")

    return output_path


@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("👋 Send me a YouTube link and I’ll show you available download options!")

@app.on_message(filters.text & filters.private)
async def handle_youtube_link(client, message):
    url = message.text.strip()

    if "youtube.com" in url or "youtu.be" in url:
        await message.reply("🔍 Processing the video... Please wait.")
        try:
            formats = get_merged_formats(url)
        except Exception as e:
            return await message.reply(f"❌ Failed to fetch formats.\nError: {e}")

        if not formats:
            return await message.reply("❌ No valid formats with sound found.")

        buttons = []
        for fmt in formats:
            size_mb = fmt["filesize"] / (1024 * 1024)
            label = f'{fmt["quality"]} | {readable_size(fmt["filesize"])}'

            if size_mb <= MAX_SIZE_MB:
                buttons.append([InlineKeyboardButton(label, callback_data=f'dl|{url}|{fmt["format_id"]}')])
            else:
                buttons.append([InlineKeyboardButton(f'{label} 🚫 >50MB', callback_data="too_big")])

        await message.reply("🎬 Choose a quality to download:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply("⚠️ Only YouTube links are supported for now.")

@app.on_callback_query()
async def handle_button(client, callback):
    data = callback.data

    if data == "too_big":
        await callback.answer("❌ File too large for Telegram (over 50MB)", show_alert=True)
        return

    await callback.answer("⏬ Downloading... please wait.")
    await callback.message.edit_text("📥 Downloading video...")

    _, url, format_id = data.split("|")

    try:
        from yt_dlp import YoutubeDL
        ydl_opts = {
            'format': f'{format_id}/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'merge_output_format': 'mp4',
            'ffmpeg_location': '/usr/bin/ffmpeg',
        }

        os.makedirs("downloads", exist_ok=True)

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        all_files = os.listdir("downloads")
        await callback.message.reply(f"📂 Files in folder: {all_files}")

        files = glob.glob("**/*.mp4", recursive=True)
        if not files:
            raise Exception("❌ No video file found after download.")

        filename = max(files, key=os.path.getctime)
        await callback.message.reply(f"📁 Detected: `{filename}`")

        time.sleep(1.5)
        converted_file = reencode_video(filename)

        await client.send_video(
            chat_id=callback.message.chat.id,
            video=converted_file,
            caption=f"🎬 {info.get('title', 'Here is your video')}"
        )

        os.remove(filename)
        os.remove(converted_file)
        if os.path.exists("downloads/input_safe.mp4"):
            os.remove("downloads/input_safe.mp4")

    except Exception as e:
        error_text = str(e)
        if len(error_text) > 4000:
            error_text = error_text[:3990] + '... (truncated)'
        try:
            await callback.message.reply(f"❌ Failed to download.\n\n**Reason:**\n`{error_text}`")
        except Exception:
            await client.send_message(callback.message.chat.id, f"❌ Failed.\nReason:\n`{error_text}`")

app.run()
