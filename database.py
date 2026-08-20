# bot developer @iamak_roy
from os import environ 
from config import Config
import motor.motor_asyncio
from pymongo import MongoClient
from typing import Optional, Dict, List, Union

async def mongodb_version():
    x = MongoClient(Config.DATABASE_URI)
    mongodb_version = x.server_info()['version']
    return mongodb_version

class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.bot = self.db.bots
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels
        self.jobs = self.db.forward_jobs  # persistent forward jobs for resume 
        
    def new_user(self, id, name):
        return dict(
            id=id,
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            regex_pattern="",  # Added for regex pattern storage
            configs={
                'caption': None,
                'duplicate': True,
                'forward_tag': False,
                'file_size': 0,
                'size_limit': None,
                'extension': None,
                'keywords': None,
                'protect': None,
                'button': None,
                'db_uri': None,
                'min_views': 0,          # NEW: Minimum views to forward (0 = off)
                'top_n': 0,             # NEW: Only top N by views (0 = off)
                'filters': {
                    'poll': True,
                    'text': True,
                    'audio': True,
                    'voice': True,
                    'video': True,
                    'photo': True,
                    'document': True,
                    'animation': True,
                    'sticker': True
                }
            }
        )
      
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)
    
    async def total_users_bots_count(self):
        bcount = await self.bot.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount

    async def total_channels(self):
        count = await self.chl.count_documents({})
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id': int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})
    
    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})
 
    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        b_users = [user['id'] async for user in users]
        return b_users

    async def update_configs(self, id, configs):
        await self.col.update_one({'id': int(id)}, {'$set': {'configs': configs}})
         
    async def get_configs(self, id):
        default = self.new_user(0, "")['configs']  # Get default config from new_user
        user = await self.col.find_one({'id': int(id)})
        if user:
            return user.get('configs', default)
        return default

    # Regex Pattern Functions
    async def update_user_regex(self, user_id: int, pattern: str) -> bool:
        """Store user's regex pattern for filtering"""
        try:
            await self.col.update_one(
                {'id': int(user_id)},
                {'$set': {'regex_pattern': pattern}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating regex pattern: {e}")
            return False

    async def get_user_regex(self, user_id: int) -> Optional[str]:
        """Retrieve user's regex pattern"""
        user = await self.col.find_one({'id': int(user_id)})
        return user.get('regex_pattern', "") if user else None

    async def clear_user_regex(self, user_id: int) -> bool:
        """Remove user's regex pattern"""
        try:
            await self.col.update_one(
                {'id': int(user_id)},
                {'$unset': {'regex_pattern': ""}}
            )
            return True
        except Exception as e:
            print(f"Error clearing regex pattern: {e}")
            return False
       
    async def add_bot(self, datas):
        """Add bot/userbot. Max 5 per user."""
        count = await self.bot.count_documents({'user_id': int(datas['user_id'])})
        if count >= 5:
            return False  # limit reached
        await self.bot.insert_one(datas)
        return True
    
    async def remove_bot(self, user_id, bot_id=None):
        """Remove one bot by _id or all bots of user"""
        if bot_id:
            from bson import ObjectId
            try:
                await self.bot.delete_one({'_id': ObjectId(bot_id), 'user_id': int(user_id)})
            except:
                await self.bot.delete_one({'_id': bot_id, 'user_id': int(user_id)})
        else:
            await self.bot.delete_many({'user_id': int(user_id)})
      
    async def get_bot(self, user_id: int, bot_id=None):
        """Get one bot. If bot_id given, get specific. Else get first one (backward compatible)."""
        if bot_id:
            from bson import ObjectId
            try:
                bot = await self.bot.find_one({'_id': ObjectId(bot_id), 'user_id': int(user_id)})
            except:
                bot = await self.bot.find_one({'_id': bot_id, 'user_id': int(user_id)})
            return bot if bot else None
        bot = await self.bot.find_one({'user_id': int(user_id)})
        return bot if bot else None

    async def get_all_bots(self, user_id: int):
        """Get all bots/userbots of a user (max 5)"""
        bots = self.bot.find({'user_id': int(user_id)})
        return [b async for b in bots]
                                          
    async def is_bot_exist(self, user_id):
        bot = await self.bot.find_one({'user_id': int(user_id)})
        return bool(bot)

    async def bot_count(self, user_id: int):
        return await self.bot.count_documents({'user_id': int(user_id)})
                                          
    async def in_channel(self, user_id: int, chat_id: int) -> bool:
        channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
        return bool(channel)
    
    async def add_channel(self, user_id: int, chat_id: int, title, username):
        channel = await self.in_channel(user_id, chat_id)
        if channel:
            return False
        return await self.chl.insert_one({
            "user_id": user_id, 
            "chat_id": chat_id, 
            "title": title, 
            "username": username
        })
    
    async def remove_channel(self, user_id: int, chat_id: int):
        channel = await self.in_channel(user_id, chat_id)
        if not channel:
            return False
        return await self.chl.delete_many({
            "user_id": int(user_id), 
            "chat_id": int(chat_id)
        })
    
    async def get_channel_details(self, user_id: int, chat_id: int):
        return await self.chl.find_one({
            "user_id": int(user_id), 
            "chat_id": int(chat_id)
        })
       
    async def get_user_channels(self, user_id: int):
        channels = self.chl.find({"user_id": int(user_id)})
        return [channel async for channel in channels]
     
    async def get_filters(self, user_id):
        filters = []
        filter = (await self.get_configs(user_id))['filters']
        for k, v in filter.items():
            if v == False:
                filters.append(str(k))
        return filters
              
    async def add_frwd(self, user_id):
        return await self.nfy.insert_one({'user_id': int(user_id)})
    
    async def rmve_frwd(self, user_id=0, all=False):
        data = {} if all else {'user_id': int(user_id)}
        return await self.nfy.delete_many(data)
    
    async def get_all_frwd(self):
        return self.nfy.find({})

    # ========== Persistent Forward Jobs (for resume after restart) ==========
    
    async def save_job(self, job_data: dict):
        """Save or update a forward job. job_data must have 'job_id'."""
        job_id = job_data.get('job_id')
        if not job_id:
            return False
        job_data['updated_at'] = __import__('time').time()
        await self.jobs.update_one(
            {'job_id': job_id},
            {'$set': job_data},
            upsert=True
        )
        return True

    async def update_job_progress(self, job_id: str, current_id: int, fetched: int = 0, forwarded: int = 0):
        """Update progress of a running job so it can resume."""
        await self.jobs.update_one(
            {'job_id': job_id},
            {'$set': {
                'current_id': current_id,
                'fetched': fetched,
                'forwarded': forwarded,
                'updated_at': __import__('time').time(),
                'status': 'running'
            }}
        )

    async def get_job(self, job_id: str):
        return await self.jobs.find_one({'job_id': job_id})

    async def get_pending_jobs(self, user_id: int = None):
        """Get jobs that are still running / incomplete."""
        query = {'status': {'$in': ['running', 'pending']}}
        if user_id:
            query['user_id'] = int(user_id)
        return [j async for j in self.jobs.find(query)]

    async def complete_job(self, job_id: str):
        await self.jobs.update_one(
            {'job_id': job_id},
            {'$set': {'status': 'completed', 'updated_at': __import__('time').time()}}
        )

    async def cancel_job(self, job_id: str):
        await self.jobs.update_one(
            {'job_id': job_id},
            {'$set': {'status': 'cancelled', 'updated_at': __import__('time').time()}}
        )

    async def delete_job(self, job_id: str):
        await self.jobs.delete_one({'job_id': job_id})

    async def clear_old_jobs(self, max_age_hours=48):
        """Clean completed/cancelled jobs older than max_age_hours."""
        cutoff = __import__('time').time() - (max_age_hours * 3600)
        await self.jobs.delete_many({
            'status': {'$in': ['completed', 'cancelled']},
            'updated_at': {'$lt': cutoff}
        })

db = Database(Config.DATABASE_URI, Config.DATABASE_NAME)
