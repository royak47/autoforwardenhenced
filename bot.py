import asyncio
import logging
import logging.config
import random
import aiohttp
from os import environ

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


# 🔁 Strong Keep-Alive (multiple URLs + frequent ping)
async def auto_ping():
    urls = []
    
    # Primary URL from env
    primary = environ.get("RENDER_EXTERNAL_URL") or environ.get("PING_URL")
    if primary:
        urls.append(primary.rstrip('/'))
    
    # Always ping local flask too
    urls.append("http://127.0.0.1:10000")
    urls.append("http://0.0.0.0:10000")
    
    # Extra backup pings (user can set PING_URL_2, PING_URL_3)
    for key in ["PING_URL_2", "PING_URL_3", "PING_URL_4"]:
        extra = environ.get(key)
        if extra:
            urls.append(extra.rstrip('/'))
    
    # Remove duplicates
    urls = list(dict.fromkeys(urls))
    
    logging.info(f"Keep-alive URLs: {urls}")
    
    while True:
        for url in urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        logging.info(f"✅ Ping {url} → {resp.status}")
            except Exception as e:
                logging.warning(f"❌ Ping failed {url}: {e}")
        
        # Every 3-5 minutes (Render free sleeps ~15 min)
        wait_time = random.randint(180, 300)
        await asyncio.sleep(wait_time)


async def resume_pending_jobs(bot_client):
    """On startup, find incomplete jobs and notify user + try to resume."""
    try:
        pending = await db.get_pending_jobs()
        if not pending:
            logging.info("No pending forward jobs to resume.")
            return
        
        logging.info(f"Found {len(pending)} pending job(s) to resume.")
        
        for job in pending:
            user_id = job.get('user_id')
            job_id = job.get('job_id')
            current = job.get('current_id', job.get('skip', 0))
            limit = job.get('limit', 0)
            forwarded = job.get('forwarded', 0)
            
            try:
                await bot_client.send_message(
                    user_id,
                    f"<b>♻️ Bot Restarted — Incomplete Job Found</b>\n\n"
                    f"Job: <code>{job_id}</code>\n"
                    f"Progress: ~{forwarded} messages forwarded\n"
                    f"Last position: <code>{current}</code> / <code>{limit}</code>\n\n"
                    f"<b>Resume karne ke liye:</b>\n"
                    f"1. /forward dobara chalao\n"
                    f"2. Same source message do\n"
                    f"3. Direction + count same rakho\n"
                    f"   (ya skip = {current} set karke continue karo)\n\n"
                    f"<i>Job abhi bhi database mein saved hai.</i>"
                )
            except Exception as e:
                logging.warning(f"Could not notify user {user_id}: {e}")
        
        # Clean very old completed jobs
        await db.clear_old_jobs(48)
        
    except Exception as e:
        logging.error(f"Resume jobs error: {e}")


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

        logging.info(f"{me.first_name} with pyrogram v{__version__} (Layer {layer}) started on @{me.username}.")
        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        self.set_parse_mode(ParseMode.DEFAULT)

        # ⏳ Start keep-alive ping
        asyncio.create_task(auto_ping())
        
        # ♻️ Check & notify pending jobs for resume
        asyncio.create_task(resume_pending_jobs(self))

        # 🔁 Notify users who had active forward (old system)
        text = "**♻️ Bot restarted!**\n\nAgar koi forward incomplete tha to uska detail aapko alag message mein mil jayega."
        logging.info("Bot restarted notification...")
        success = failed = 0

        users = await db.get_all_frwd()
        async for user in users:
            chat_id = user['user_id']
            try:
                await self.send_message(chat_id, text)
                success += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    await self.send_message(chat_id, text)
                    success += 1
                except:
                    failed += 1
            except Exception:
                failed += 1

        if (success + failed) != 0:
            await db.rmve_frwd(all=True)
            logging.info(f"Restart notify → success: {success} | failed: {failed}")

    async def stop(self, *args):
        msg = f"@{self.username} stopped. Bye."
        await super().stop()
        logging.info(msg)
