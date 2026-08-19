import asyncio
import logging
import logging.config
import random
import aiohttp

from database import db
from config import Config
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

# bot developer @iamak_roy / @mr_jisshu

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# 🔁 Auto ping task to keep bot alive
async def auto_ping():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://autoforwardbeta-1.onrender.com") as resp:
                    if resp.status == 200:
                        logging.info("✅ Auto ping successful.")
                    else:
                        logging.warning(f"⚠️ Auto ping failed with status: {resp.status}")
        except Exception as e:
            logging.warning(f"❌ Auto ping error: {e}")
        
        wait_time = random.randint(300, 600)  # 5 to 10 minutes
        await asyncio.sleep(wait_time)

class Bot(Client):
    def __init__(self):
        super().__init__(
            Config.BOT_SESSION,
            api_hash=Config.API_HASH,
            api_id=Config.API_ID,
            plugins={"root": "plugins"},
            workers=50,
            bot_token=Config.BOT_TOKEN
        )
        self.log = logging

    async def start(self):
        await super().start()
        me = await self.get_me()

        logging.info(f"{me.first_name} with for pyrogram v{__version__} (Layer {layer}) started on @{me.username}.")
        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        self.set_parse_mode(ParseMode.DEFAULT)

        # ⏳ Start the ping task
        asyncio.create_task(auto_ping())

        # 🔁 Notify forward users
        text = "**๏[-ิ_•ิ]๏ bot restarted !**"
        logging.info(text)
        success = failed = 0

        users = await db.get_all_frwd()
        async for user in users:
            chat_id = user['user_id']
            try:
                await self.send_message(chat_id, text)
                success += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                await self.send_message(chat_id, text)
                success += 1
            except Exception:
                failed += 1

        if (success + failed) != 0:
            await db.rmve_frwd(all=True)
            logging.info(f"Restart message status success: {success} | failed: {failed}")

    async def stop(self, *args):
        msg = f"@{self.username} stopped. Bye."
        await super().stop()
        logging.info(msg)
