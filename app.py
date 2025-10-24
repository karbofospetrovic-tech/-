import os
import tempfile
import subprocess
from aiogram import Bot, Dispatcher, types, executor
from googletrans import Translator
from gtts import gTTS
import whisper

# === Настройки ===
BOT_TOKEN = "ВСТАВЬ_СВОЙ_TELEGRAM_ТОКЕН"
translator = Translator()
model = whisper.load_model("small")  # можно "tiny" для слабого ПК

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- Вспомогательные функции ---
def convert_ogg_to_wav(input_path: str) -> str:
    out_path = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", out_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    return out_path

def tts(text, lang):
    path = tempfile.mktemp(suffix=".mp3")
    gTTS(text=text, lang=lang).save(path)
    return path

# --- Обработка текстовых сообщений ---
@dp.message_handler(content_types=["text"])
async def handle_text(msg: types.Message):
    text = msg.text.strip()
    # Определяем направление перевода
    src_lang = "ru" if all("а" <= c.lower() <= "я" for c in text if c.isalpha()) else "de"
    dest_lang = "de" if src_lang == "ru" else "ru"
    translated = translator.translate(text, src=src_lang, dest=dest_lang).text
    await msg.reply(f"🔤 Перевод:\n{translated}")

    # Озвучка
    voice_path = tts(translated, dest_lang)
    with open(voice_path, "rb") as f:
        await bot.send_audio(msg.chat.id, f, caption="🔊 Озвучка перевода")
    os.remove(voice_path)

# --- Обработка голосовых сообщений ---
@dp.message_handler(content_types=["voice"])
async def handle_voice(msg: types.Message):
    await msg.reply("🎧 Распознаю речь...")
    file_info = await bot.get_file(msg.voice.file_id)
    ogg_path = tempfile.mktemp(suffix=".ogg")
    await bot.download_file(file_info.file_path, ogg_path)

    # Конвертируем ogg -> wav
    wav_path = convert_ogg_to_wav(ogg_path)
    # Распознаём текст через Whisper
    result = model.transcribe(wav_path, fp16=False, language=None)
    text = result["text"].strip()
    await msg.reply(f"🗣 Распознано:\n{text}")

    # Определяем направление
    src_lang = "ru" if any("а" <= c.lower() <= "я" for c in text if c.isalpha()) else "de"
    dest_lang = "de" if src_lang == "ru" else "ru"

    # Перевод
    translated = translator.translate(text, src=src_lang, dest=dest_lang).text
    await msg.reply(f"🔤 Перевод:\n{translated}")

    # Озвучка
    voice_path = tts(translated, dest_lang)
    with open(voice_path, "rb") as f:
        await bot.send_audio(msg.chat.id, f, caption="🔊 Озвучка перевода")

    os.remove(ogg_path)
    os.remove(wav_path)
    os.remove(voice_path)

if __name__ == "__main__":
    print("✅ Бот запущен")
    executor.start_polling(dp, skip_updates=True)


