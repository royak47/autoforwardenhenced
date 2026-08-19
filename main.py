from bot import Bot
from flask import Flask
from threading import Thread

app = Bot()

web = Flask(__name__)

@web.route('/')
def home():
    return 'Bot is running by @iamak_roy'

def run_flask():
    web.run(host='0.0.0.0', port=10000)

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    app.run()
