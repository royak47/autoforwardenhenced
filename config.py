# bot developer @mr_jisshu
from os import environ 

class Config:
    
    API_ID = environ.get("API_ID", "")
    API_HASH = environ.get("API_HASH", "")
    BOT_TOKEN = environ.get("BOT_TOKEN", "") 
    
    # Owner IDs (space separated)
    _owner = environ.get("BOT_OWNER_ID", "") or environ.get("OWNER_ID", "")
    BOT_OWNER_ID = [int(id) for id in _owner.split() if id.strip().isdigit()]
    
    BOT_SESSION = environ.get("BOT_SESSION", "bot") 

    PICS = environ.get('PICS', 'https://i.ibb.co/zYTL2cG/temp.jpg')
    
    DATABASE_URI = environ.get("DATABASE_URI", "")
    DATABASE_NAME = environ.get("DATABASE_NAME", "Cluster0")
    
    # Safe conversion for LOG_CHANNEL
    try:
        LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '0'))
    except:
        LOG_CHANNEL = 0
    
    FORCE_SUB_CHANNEL = environ.get("FORCE_SUB_CHANNEL", "")
    
    # Default OFF so /start works even if no force sub channel is set
    FORCE_SUB_ON = environ.get("FORCE_SUB_ON", "False").lower() in ["true", "1", "yes"]


class temp(object): 
    lock = {}
    CANCEL = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []
