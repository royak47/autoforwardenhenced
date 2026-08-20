from bot import Bot
from flask import Flask
from threading import Thread
import os

app = Bot()

web = Flask(__name__)

@web.route('/')
def home():
    return '✅ AutoForward Bot is running 24/7', 200

@web.route('/health')
def health():
    return {'status': 'ok', 'bot': 'alive'}, 200

@web.route('/ping')
def ping():
    return 'pong', 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web.run(host='0.0.0.0', port=port, threaded=True)

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    app.run()
