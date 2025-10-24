import os
import logging
import tempfile
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import speech_recognition as sr
from gtts import gTTS
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app для Fly.io
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот Братик работает!"

# Функция перевода текста
def translate_text(text, target_lang='ru'):
    try:
        # Определяем исходный язык
        if any(char in 'äöüß' for char in text.lower()):
            source_lang = 'de'  # немецкий
            target_lang = 'ru' if target_lang == 'ru' else 'de'
        else:
            source_lang = 'ru'  # русский
            target_lang = 'de' if target_lang == 'de' else 'ru'
        
        # Перевод
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        return translated
    except Exception as e:
        return f"Ошибка перевода: {e}"

# Функция преобразования текста в речь
def text_to_speech(text, lang='ru'):
    try:
        tts = gTTS(text=text, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            tts.save(fp.name)
            return fp.name
    except Exception as e:
        logger.error(f"Ошибка TTS: {e}")
        return None

# Функция распознавания речи
def speech_to_text(audio_file):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language='ru-RU')
            return text
    except sr.UnknownValueError:
        return "Не удалось распознать речь"
    except Exception as e:
        logger.error(f"Ошибка распознавания: {e}")
        return f"Ошибка: {e}"

# Обработчик текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Автоматически определяем направление перевода
    translated = translate_text(text)
    
    await update.message.reply_text(f"Перевод:\n{translated}")

# Обработчик голосовых сообщений
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
        
        # Скачиваем голосовое сообщение
        voice_file = await update.message.voice.get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as ogg_file:
            await voice_file.download_to_drive(ogg_file.name)
            
            # Конвертируем ogg в wav для распознавания
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as wav_file:
                # Используем pydub для конвертации
                from pydub import AudioSegment
                audio = AudioSegment.from_ogg(ogg_file.name)
                audio.export(wav_file.name, format="wav")
                
                # Распознаем речь
                recognized_text = speech_to_text(wav_file.name)
                
                if "Не удалось" in recognized_text or "Ошибка" in recognized_text:
                    await update.message.reply_text(f"❌ {recognized_text}")
                    return
                
                await update.message.reply_text(f"🎤 Распознано: {recognized_text}")
                
                # Переводим текст
                translated = translate_text(recognized_text)
                await update.message.reply_text(f"🌍 Перевод: {translated}")
                
                # Преобразуем перевод в речь
                if any(char in 'äöüß' for char in recognized_text.lower()):
                    # Немецкий -> русский, озвучиваем по-русски
                    tts_file = text_to_speech(translated, 'ru')
                    tts_lang = 'ru'
                else:
                    # Русский -> немецкий, озвучиваем по-немецки
                    tts_file = text_to_speech(translated, 'de')
                    tts_lang = 'de'
                
                if tts_file:
                    await update.message.reply_voice(
                        voice=open(tts_file, 'rb'),
                        caption=f"🔊 Озвучка перевода ({'русский' if tts_lang == 'ru' else 'немецкий'})"
                    )
                    os.unlink(tts_file)
                
                # Удаляем временные файлы
                os.unlink(ogg_file.name)
                os.unlink(wav_file.name)
                
    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}")
        await update.message.reply_text("❌ Ошибка обработки голосового сообщения")

# Команда старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я Братик - переводчик 🇩🇪⇄🇷🇺\n\n"
        "📝 *Текстовые сообщения:* автоматически перевожу между русским и немецким\n"
        "🎤 *Голосовые сообщения:* распознаю, перевожу и озвучиваю перевод\n\n"
        "Просто отправь мне текст или голосовое сообщение!",
        parse_mode='Markdown'
    )

def main():
    # Создаем приложение Flask для Fly.io
    @app.route('/health')
    def health():
        return "OK"
    
    # Запускаем Flask (для Fly.io)
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
    
    # Инициализация бота
    token = "8083120011:AAHs2PDQSa1GmOHJ7RzfoXbIc3Q87174VYU"
    if token:
        bot_app = Application.builder().token(token).build()
        
        # Добавляем обработчики
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        bot_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        from telegram.ext import CommandHandler
        bot_app.add_handler(CommandHandler("start", start))
        
        # Запускаем бота в отдельном потоке
        import threading
        def run_bot():
            logger.info("Запускаем бота...")
            bot_app.run_polling()
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        logger.info("Бот Братик запущен!")

if __name__ == '__main__':
    main()