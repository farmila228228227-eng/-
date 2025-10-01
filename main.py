import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

# 🔑 Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")  # токен берём из Secrets
OWNER_ID = 7322925570  # твой айди

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

# 📂 Работа с данными
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chats": [], "interval_min": 5, "message": "Привет!", "running": False}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

data = load_data()

# 📌 Только для владельца
def owner_only(func):
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id != OWNER_ID:
            return
        return await func(message, *args, **kwargs)
    return wrapper

# 🚀 Рассылка
async def sender():
    while data.get("running"):
        for chat in data["chats"]:
            try:
                await bot.send_message(
                    chat["chat_id"], data["message"], message_thread_id=chat.get("topic_id")
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке в {chat}: {e}")
        await asyncio.sleep(data["interval_min"] * 60)

sender_task = None

async def start_sender():
    global sender_task
    if sender_task is None or sender_task.done():
        sender_task = asyncio.create_task(sender())

async def stop_sender():
    global sender_task
    if sender_task and not sender_task.done():
        sender_task.cancel()
        try:
            await sender_task
        except asyncio.CancelledError:
            pass
    sender_task = None

# 📌 Команды
@dp.message(Command("start"))
@owner_only
async def cmd_start(message: Message):
    await message.reply("✅ Бот запущен. Используй /help для списка команд.")

@dp.message(Command("help"))
@owner_only
async def cmd_help(message: Message):
    await message.reply(
        "📌 Команды:\n"
        "/addchat <chat_id> [topic_id] — добавить чат/тему\n"
        "/addhere — добавить текущий чат (и тему если есть)\n"
        "/delchat <chat_id> [topic_id] — удалить чат/тему\n"
        "/delhere — удалить текущий чат (и тему если есть)\n"
        "/listchats — список чатов\n"
        "/setinterval <мин> — интервал (1-60)\n"
        "/setmessage <текст> — сообщение для рассылки\n"
        "/startspam — начать рассылку\n"
        "/stopspam — остановить рассылку\n"
        "/getid — показать ID чата и темы"
    )

@dp.message(Command("getid"))
@owner_only
async def cmd_getid(message: Message):
    chat_id = message.chat.id
    thread_id = getattr(message, "message_thread_id", None)
    if thread_id:
        await message.reply(f"📌 Chat ID: `{chat_id}`\n🧵 Topic ID: `{thread_id}`", parse_mode="Markdown")
    else:
        await message.reply(f"📌 Chat ID: `{chat_id}`\n(без топика)", parse_mode="Markdown")

@dp.message(Command("addchat"))
@owner_only
async def cmd_addchat(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("❌ Использование: /addchat <chat_id> [topic_id]")
    chat_id = int(parts[1])
    topic_id = int(parts[2]) if len(parts) > 2 else None
    chat = {"chat_id": chat_id}
    if topic_id:
        chat["topic_id"] = topic_id
    if chat not in data["chats"]:
        data["chats"].append(chat)
        save_data(data)
        await message.reply("✅ Чат добавлен.")
    else:
        await message.reply("⚠️ Такой чат уже есть.")

@dp.message(Command("addhere"))
@owner_only
async def cmd_addhere(message: Message):
    chat_id = message.chat.id
    thread_id = getattr(message, "message_thread_id", None)
    chat = {"chat_id": chat_id}
    if thread_id:
        chat["topic_id"] = thread_id
    if chat not in data["chats"]:
        data["chats"].append(chat)
        save_data(data)
        await message.reply("✅ Текущий чат добавлен.")
    else:
        await message.reply("⚠️ Этот чат уже есть.")

@dp.message(Command("delchat"))
@owner_only
async def cmd_delchat(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("❌ Использование: /delchat <chat_id> [topic_id]")
    chat_id = int(parts[1])
    topic_id = int(parts[2]) if len(parts) > 2 else None
    before = len(data["chats"])
    data["chats"] = [c for c in data["chats"] if not (c["chat_id"] == chat_id and c.get("topic_id") == topic_id)]
    after = len(data["chats"])
    save_data(data)
    if before != after:
        await message.reply("✅ Чат удалён.")
    else:
        await message.reply("⚠️ Чат не найден.")

@dp.message(Command("delhere"))
@owner_only
async def cmd_delhere(message: Message):
    chat_id = message.chat.id
    thread_id = getattr(message, "message_thread_id", None)
    before = len(data["chats"])
    data["chats"] = [c for c in data["chats"] if not (c["chat_id"] == chat_id and c.get("topic_id") == thread_id)]
    after = len(data["chats"])
    save_data(data)
    if before != after:
        await message.reply("✅ Текущий чат удалён.")
    else:
        await message.reply("⚠️ Этот чат не найден.")

@dp.message(Command("listchats"))
@owner_only
async def cmd_listchats(message: Message):
    if not data["chats"]:
        return await message.reply("📭 Список чатов пуст.")
    text = "📌 Чаты для рассылки:\n"
    for c in data["chats"]:
        text += f"- {c['chat_id']}"
        if "topic_id" in c:
            text += f" (topic {c['topic_id']})"
        text += "\n"
    await message.reply(text)

@dp.message(Command("setinterval"))
@owner_only
async def cmd_setinterval(message: Message):
    args = message.text.replace("/setinterval", "", 1).strip()
    try:
        m = int(args)
        if not (1 <= m <= 60):
            raise ValueError
    except Exception:
        return await message.reply("❌ Интервал должен быть числом от 1 до 60.")
    data["interval_min"] = m
    save_data(data)
    await stop_sender()
    if data.get("running"):
        await start_sender()
    await message.reply(f"✅ Интервал установлен: {m} мин.")

@dp.message(Command("setmessage"))
@owner_only
async def cmd_setmessage(message: Message):
    args = message.text.replace("/setmessage", "", 1).strip()
    if not args:
        return await message.reply("❌ Использование: /setmessage <текст>")
    data["message"] = args
    save_data(data)
    await message.reply("✅ Сообщение обновлено.")

@dp.message(Command("startspam"))
@owner_only
async def cmd_startspam(message: Message):
    data["running"] = True
    save_data(data)
    await start_sender()
    await message.reply("🚀 Рассылка запущена.")

@dp.message(Command("stopspam"))
@owner_only
async def cmd_stopspam(message: Message):
    data["running"] = False
    save_data(data)
    await stop_sender()
    await message.reply("⛔ Рассылка остановлена.")

# 🔄 Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
