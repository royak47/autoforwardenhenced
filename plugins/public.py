import re
import asyncio 
from .utils import STS
from database import db
from config import temp 
from translation import Translation
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
 
#===================Run Function===================#

@Client.on_message(filters.private & filters.command(["fwd", "forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id
    
    all_bots = await db.get_all_bots(user_id)
    if not all_bots:
      return await message.reply("<code>You didn't added any bot/userbot.\nPlease add using /settings !</code>")
    
    # ===== Choose Bot / Userbot (if more than 1) =====
    if len(all_bots) == 1:
        _bot = all_bots[0]
    else:
        bot_map = {}
        btn_list = []
        for b in all_bots:
            btype = "🤖" if b.get('is_bot') else "👤"
            name = b.get('name', 'Unknown')
            key = f"{btype} {name}"
            btn_list.append([KeyboardButton(key)])
            bot_map[key] = b
        btn_list.append([KeyboardButton("cancel")])
        
        choice = await bot.ask(
            message.chat.id,
            f"<b>Kaunsa Bot / Userbot use karna hai?</b>\n\nTotal added: {len(all_bots)}/5",
            reply_markup=ReplyKeyboardMarkup(btn_list, one_time_keyboard=True, resize_keyboard=True)
        )
        if choice.text.startswith(('/', 'cancel')):
            return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
        _bot = bot_map.get(choice.text)
        if not _bot:
            return await message.reply_text("Galat choice!", reply_markup=ReplyKeyboardRemove())
    
    channels = await db.get_user_channels(user_id)
    if not channels:
       return await message.reply_text("please set a to channel in /settings before forwarding", reply_markup=ReplyKeyboardRemove())
    
    # ===== Target Channel Selection =====
    if len(channels) > 1:
       for channel in channels:
          buttons.append([KeyboardButton(f"{channel['title']}")])
          btn_data[channel['title']] = channel['chat_id']
       buttons.append([KeyboardButton("cancel")]) 
       _toid = await bot.ask(message.chat.id, Translation.TO_MSG.format(_bot['name'], _bot.get('username', '')), reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))
       if _toid.text.startswith(('/', 'cancel')):
          return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
       to_title = _toid.text
       toid = btn_data.get(to_title)
       if not toid:
          return await message.reply_text("wrong channel choosen !", reply_markup=ReplyKeyboardRemove())
    else:
       toid = channels[0]['chat_id']
       to_title = channels[0]['title']
    
    # ===== Source Message / Link =====
    fromid = await bot.ask(
        message.chat.id, 
        "<b>📌 Source Message bhejo</b>\n\n"
        "• Kisi message ka <b>link</b> bhejo\n"
        "• Ya us message ko <b>forward</b> kar do\n\n"
        "<i>Ye reference message hoga. Iske aage ya piche ke messages forward honge.</i>\n\n"
        "/cancel - cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    
    if fromid.text and fromid.text.startswith('/'):
        await message.reply(Translation.CANCEL)
        return 
    
    if fromid.text and not fromid.forward_date:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(fromid.text.replace("?single", ""))
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        ref_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int(("-100" + chat_id))
    elif fromid.forward_from_chat and fromid.forward_from_chat.type in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
        ref_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        if ref_msg_id is None:
           return await message.reply_text("**Anonymous admin ka message lag raha hai. Please us message ka direct link bhejo.**")
    else:
        await message.reply_text("**Invalid! Link ya forward message bhejo.**")
        return 
    
    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = "private" if fromid.text else fromid.forward_from_chat.title
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')
    
    # ===== Direction Choice (Aage / Piche) =====
    dir_buttons = ReplyKeyboardMarkup(
        [
            [KeyboardButton("⬅️ Piche Wale (Older)")],
            [KeyboardButton("➡️ Aage Wale (Newer)")],
            [KeyboardButton("cancel")]
        ],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    direction_msg = await bot.ask(
        message.chat.id,
        f"<b>📍 Reference Message:</b> <code>{ref_msg_id}</code>\n"
        f"<b>Source:</b> {title}\n\n"
        "<b>Kaunse messages forward karne hain?</b>\n\n"
        "⬅️ <b>Piche Wale</b> → Is message se pehle ke (older) messages\n"
        "➡️ <b>Aage Wale</b> → Is message ke baad ke (newer) messages\n\n"
        "/cancel - cancel",
        reply_markup=dir_buttons
    )
    
    if direction_msg.text.startswith(('/', 'cancel')):
        return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
    
    direction = "older"
    if "Aage" in direction_msg.text or "Newer" in direction_msg.text or "➡️" in direction_msg.text:
        direction = "newer"
    elif "Piche" in direction_msg.text or "Older" in direction_msg.text or "⬅️" in direction_msg.text:
        direction = "older"
    else:
        return await message.reply_text("Galat option! Dobara /forward try karo.", reply_markup=ReplyKeyboardRemove())
    
    # ===== How many messages =====
    count_msg = await bot.ask(
        message.chat.id,
        f"<b>Kitne messages forward karne hain?</b>\n\n"
        f"Reference: <code>{ref_msg_id}</code>\n"
        f"Direction: <b>{'➡️ Aage (Newer)' if direction == 'newer' else '⬅️ Piche (Older)'}</b>\n\n"
        "Sirf number bhejo (example: <code>100</code> / <code>500</code> / <code>2000</code>)\n\n"
        "/cancel - cancel",
        reply_markup=ReplyKeyboardRemove()
    )
    
    if count_msg.text.startswith('/'):
        return await message.reply(Translation.CANCEL)
    
    try:
        count = int(count_msg.text.strip().replace(',', ''))
        if count < 1:
            return await message.reply("Kam se kam 1 message to bhejo.")
        if count > 100000:
            return await message.reply("Bahut zyada hai. Maximum 100000 tak try karo.")
    except:
        return await message.reply("Sahi number bhejo (sirf digits).")
    
    # ===== Calculate start & limit based on direction =====
    if direction == "older":
        # Piche = older messages (lower IDs)
        # We go from (ref_msg_id - count) to ref_msg_id
        start_id = max(1, ref_msg_id - count)
        end_id = ref_msg_id
        skip = start_id
        limit = end_id
        dir_text = "⬅️ Piche Wale (Older)"
    else:
        # Aage = newer messages (higher IDs)
        # We go from ref_msg_id to (ref_msg_id + count)
        start_id = ref_msg_id
        end_id = ref_msg_id + count
        skip = start_id
        limit = end_id
        dir_text = "➡️ Aage Wale (Newer)"
    
    forward_id = f"{user_id}-{count_msg.id}"
    
    buttons = [[
        InlineKeyboardButton('✅ Yes, Start', callback_data=f"start_public_{forward_id}"),
        InlineKeyboardButton('❌ No', callback_data="close_btn")
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    confirm_text = f"""<b>📋 Double Check</b>

🤖 Bot: <b>{_bot['name']}</b> (@{_bot['username']})
📥 From: <b>{title}</b>
📤 To: <b>{to_title}</b>

📌 Reference Msg ID: <code>{ref_msg_id}</code>
📍 Direction: <b>{dir_text}</b>
🔢 Count: <b>{count}</b> messages

Range: <code>{start_id}</code> → <code>{end_id}</code>

Confirm karke Start dabao."""
    
    await message.reply_text(
        text=confirm_text,
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    
    # Store: chat_id, toid, skip (start), limit (end)
    STS(forward_id).store(chat_id, toid, skip, limit)
    
    # Extra data: selected bot + direction info
    if not hasattr(STS, 'extra'):
        STS.extra = {}
    STS.extra[forward_id] = {
        "direction": direction,
        "count": count,
        "ref_msg_id": ref_msg_id,
        "selected_bot": _bot   # the chosen bot/userbot
    }
