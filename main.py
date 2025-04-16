import os
from downloader import get_merged_formats
from yt_dlp import YoutubeDL
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = 29911242  # 🔁 Replace with your API ID
API_HASH = "dd9e829bddf9de9ce077e222fe3e2407"  # 🔁 Replace with your API HASH
BOT_TOKEN = "8150640204:AAFfeDIMWnQaWHlGtJf9mSmYpR41j0VLy2k"  # 🔁 Replace with your BotFather token


app = Client("yt_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

MAX_SIZE_MB = 50  # Telegram max upload size for free accounts


def readable_size(size_bytes):
    mb = size_bytes / (1024 * 1024)
    return f"{mb:.2f} MB"


@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "👋 Send me a YouTube link and I’ll show you available download options!"
    )


@app.on_message(filters.text & filters.private)
async def handle_youtube_link(client, message):
    url = message.text.strip()

    if "youtube.com" in url or "youtu.be" in url:
        await message.reply("🔍 Processing the video... Please wait.")

        try:
            formats = get_merged_formats(url)
        except Exception as e:
            return await message.reply(
                f"❌ Failed to fetch formats.\nError: {e}")

        if not formats:
            return await message.reply("❌ No valid formats with sound found.")

        buttons = []

        for fmt in formats:
            size_mb = fmt["filesize"] / (1024 * 1024)
            label = f'{fmt["quality"]} | {readable_size(fmt["filesize"])}'

            if size_mb <= MAX_SIZE_MB:
                buttons.append([
                    InlineKeyboardButton(
                        label, callback_data=f'dl|{url}|{fmt["format_id"]}')
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(f'{label} 🚫 >50MB',
                                         callback_data="too_big")
                ])

        await message.reply("🎬 Choose a quality to download:",
                            reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply("⚠️ Only YouTube links are supported for now.")


@app.on_callback_query()
async def handle_button(client, callback):
    data = callback.data

    if data == "too_big":
        await callback.answer("❌ File too large for Telegram (over 50MB)",
                              show_alert=True)
        return

    await callback.answer("⏬ Downloading... please wait.", show_alert=False)
    await callback.message.edit_text("📥 Downloading video...")

    _, url, format_id = data.split("|")

    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'merge_output_format': 'mp4',
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }
            ],
            'ffmpeg_location': '/usr/bin/ffmpeg'
        }



        os.makedirs("downloads", exist_ok=True)

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await client.send_video(
            chat_id=callback.message.chat.id,
            video=filename,
            caption=f"🎬 {info.get('title', 'Here is your video')}")

        os.remove(filename)  # Cleanup

    except Exception as e:
        await callback.message.reply(f"❌ Failed to download.\nError: `{e}`")


app.run()
