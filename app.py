import os
import logging
from flask import Flask

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app для Fly.io
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот Братик работает!"

@app.route('/health')
def health():
    return "OK"

def main():
    # Просто запускаем Flask
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
