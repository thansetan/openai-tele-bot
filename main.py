import logging
import os
from tempfile import TemporaryDirectory

from dotenv import load_dotenv
from open_ai import OpenAI
from pydub import AudioSegment
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      InputMediaPhoto, Update)
from telegram.error import BadRequest
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes, MessageHandler,
                          filters)

last_msg_time = {}
bot_not_allowed = "😡 You're not allowed to use this bot!"
cmd_not_allowed = "🚫 You're not allowed to use this command!"
help_message = """
*What this bot can do*:

✅ Answer your questions (*ChatGPT*) - Simply type your question and send it, and the AI will provide an answer within a few seconds.

✅ Make you 2 really cool AI-generated images (*DALL-E*) - Just type `/image <your-prompt-here>` and the AI will generate two images for you.

✅ Get a transcript of a given audio/video (*Whisper*) - There are two ways to transcribe audio. *The first one* is by recording an audio message and sending it to the bot, and *the second one* is by uploading an audio/video file and quoting the uploaded file then type `/transcribe`.


*Commands*:

⌨️ /image - Generate 2 AI-generated images based on a given prompt (usage: `/image <your-prompt-here>`).

⌨️ /transcribe - Transcribe a quoted message.

⌨️ /reset - Reset your conversation with ChatGPT.

⌨️ /help - Show help (this menu).

*Notes*: 

⚠️ The longer your conversation, the more tokens are used in each new message. So, make sure to `/reset` your conversation if you feel that your new message is not related to the previous conversation.

⚠️ For the `/transcribe` command, supported file extensions are: *mp3, mp4, mpeg, mpga, m4a, wav, and webm* with a maximum file size of *25MB*.

⚠️ For the list of languages supported by Whisper can be seen [here](https://github.com/openai/whisper#available-models-and-languages).
    """


def not_allowed(update):
    username = update.message.from_user.username
    user_id = update.message.from_user.id
    return user_id != initial_user and username not in allowed_users


async def tele_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message_text = "🤖 This bot is connected to OpenAI's API. To get an idea of what this bot is capable of, type /help."
    convo_id = update.message.from_user.id
    if convo_id in openai.conversation:
        openai.reset_conversation(convo_id)
    await context.bot.send_chat_action(chat_id, "typing")
    await context.bot.send_message(chat_id=chat_id, text=message_text)


async def tele_chat_completion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    convo_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    if last_msg_time.get(convo_id) and not not_allowed(update):
        time_diff = update.message.date - last_msg_time[convo_id]
        if time_diff.total_seconds() / 3600 > 3:
            openai.reset_conversation(convo_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⌛ Our conversation has been reset due to inactivity.",
            )
    last_msg_time[convo_id] = update.message.date
    await context.bot.send_chat_action(chat_id, "typing")
    if not_allowed(update):
        await context.bot.send_message(
            chat_id=chat_id,
            text=bot_not_allowed,
        )
    else:
        message = update.message.text
        if convo_id not in openai.conversation:
            openai.conversation.setdefault(convo_id, [])
        messages = openai.generate_messages(message, openai.conversation.get(convo_id))
        gen = openai.chat_completion(messages)
        tmp_ans = ""
        sent = False
        async for gen_item in gen:
            status, answer = gen_item
            if answer and not sent:
                msg = await context.bot.send_message(chat_id=chat_id, text=answer)
                sent = True
            if len(answer) - len(tmp_ans) < 100 and status != "finished":
                continue                
            else:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=msg.message_id,
                        text=answer,
                        parse_mode="markdown",
                    )
                except BadRequest as e:
                    if "not modified" in str(e):
                        pass
                    else:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=msg.message_id,
                            text=answer
                        )
                tmp_ans = answer


async def tele_conversation_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    convo_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    if convo_id not in openai.conversation:
        if not_allowed(update):
            text = [bot_not_allowed]
        else:
            text = [
                "😡 This is our first conversation, what do you want to reset you stoopid?"
            ]
    else:
        last_msg_time.pop(convo_id, None)
        openai.reset_conversation(convo_id)
        last_msg_time.pop(convo_id, None)
        text = [
            "🤓 Our conversation has been reset, and now it's like we're two people who have just met and don't know each other yet.",
            "🤖 Hi, I'm ChatGPT. What can I do to help you?",
        ]
    for t in text:
        await context.bot.send_message(
            chat_id=chat_id,
            text=t,
        )


async def tele_image_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message
    text = None
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    if not_allowed(update):
        text = bot_not_allowed
    else:
        message_content = message.text.split(" ", 1)
        if len(message_content) > 1:
            prompt = message_content[1]
            images = await openai.image_creation(prompt)
            image_list = [InputMediaPhoto(media=data.get("url")) for data in images]
            await context.bot.send_media_group(
                chat_id=chat_id,
                media=image_list,
                reply_to_message_id=update.message.message_id,
                caption=f"🧑🏻‍🎨: Here are 2 images of {prompt}.",
            )
        else:
            text = "🥺 Please enter the prompt (`/image <your-prompt-here>`)"
    if text:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_to_message_id=message.message_id,
            parse_mode="markdown",
        )


async def tele_audio_transcription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    allowed_files = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    is_reply = False
    max_file_size = 26214400
    message = update.message

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    if not_allowed(update):
        text = bot_not_allowed

    elif message.reply_to_message:
        is_reply = True
        quoted_message = message.reply_to_message.message_id
        file = None
        file_size = None

        if message.reply_to_message.video:
            file_size = message.reply_to_message.video.file_size
            if file_size <= max_file_size:
                file = message.reply_to_message.video.get_file()
        elif message.reply_to_message.audio:
            file_size = message.reply_to_message.audio.file_size
            if file_size <= max_file_size:
                file = message.reply_to_message.audio.get_file()
        elif message.reply_to_message.document:
            file_size = message.reply_to_message.document.file_size
            if file_size <= max_file_size:
                file = message.reply_to_message.document.get_file()
        if file:
            file = await file
            file_extension = file.file_path.split(".")[-1]
            if file_extension in allowed_files:
                file_id = file.file_id
                file_name = f"{file_id}.{file_extension}"
                text = await temp_save_and_transcribe(file, file_name)
            else:
                text = "😔 File not allowed"
        else:
            text = "😔 Invalid quoted message"
        if file_size and file_size > max_file_size:
            text = "⚠️ File size can't be more than 25 MB."
    else:
        text = "📎 To use this command, you need to reply/quote a file."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_to_message_id=quoted_message if is_reply else message.message_id,
    )


async def tele_audio_recording_transcription(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    file_id = update.message.voice.file_id
    if not_allowed(update):
        text = bot_not_allowed
    else:
        file = await context.bot.get_file(file_id)
        file_name = f"{file_id}.ogg"
        text = await temp_save_and_transcribe(file, file_name, True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def tele_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id, "typing")
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=help_message, parse_mode="markdown"
    )


async def tele_add_bot_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not_allowed(update):
        text = bot_not_allowed
    elif user_id != initial_user:
        text = cmd_not_allowed
    else:
        new_user = update.message.text.split()[1:]
        if len(new_user) > 1:
            text = "🚫 Can only add 1 user at a time."
        elif len(new_user) == 0:
            text = "🥺 Please specify who to add (`/adduser <username>`)"
        elif new_user[0] in allowed_users:
            text = f"🚫 {new_user[0]} is already on the list."
        else:
            allowed_users.append(new_user[0])
            with open("allowed_users.txt", "w") as f:
                f.write("\n".join(allowed_users))
            text = f"👌🏽 {new_user[0]} has been added to list."
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=text, parse_mode="markdown"
    )


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "cancel":
        await query.edit_message_text(text="❌ Aborting request.")
        await query.message.delete()
    else:
        num_users = query.data
        username = allowed_users[int(num_users) - 1]
        await query.answer()
        allowed_users.remove(username)
        with open("allowed_users.txt", "w") as f:
            f.write("\n".join([user for user in allowed_users]))
        await query.edit_message_text(
            text=f"🗑️ {username} has been removed and can no longer use this bot."
        )


async def tele_remove_bot_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    can_remove = False
    user_id = update.message.from_user.id

    if not_allowed(update):
        text = bot_not_allowed
    elif user_id != initial_user:
        text = cmd_not_allowed
    else:
        keyboard = []
        if len(allowed_users) != 0:
            can_remove = True
            for i, username in enumerate(allowed_users):
                button = InlineKeyboardButton(username, callback_data=f"{i+1}")
                keyboard.append([button])
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "Please select a user to remove:"
        else:
            text = "You're the only user of this bot."
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup if can_remove else None,
    )


def read_allowed_users():
    allowed_users = []
    with open("allowed_users.txt", "a+"):
        pass
    with open("allowed_users.txt", "r") as f:
        allowed_users = [user.strip() for user in f.readlines()]
    return allowed_users


def enable_logging(log_file_path):
    if log_file_path:
        if not os.path.exists(log_file_path):
            open(log_file_path, "a").close()
        logging.basicConfig(
            filename="bot.log",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.ERROR,
        )


async def temp_save_and_transcribe(file, file_name, is_voice_message=False):
    with TemporaryDirectory() as tmp_dir:
        tmp_file_path = os.path.join(tmp_dir, file_name)
        await file.download_to_drive(tmp_file_path)
        if is_voice_message:
            tmp_mp3_path = os.path.splitext(tmp_file_path)[0] + ".mp3"
            AudioSegment.from_file(tmp_file_path, format="ogg").export(
                tmp_mp3_path, format="mp3"
            )
            tmp_file_path = tmp_mp3_path
        transcript = await openai.audio_transcription(tmp_file_path)
    return (
        transcript
        if transcript.strip()
        else "I'm sorry, I cannot transcribe your audio 😞."
    )


def main():
    global initial_user, openai, allowed_users
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    initial_user = int(os.getenv("INITIAL_USER_ID"))
    log_file_path = os.getenv("LOG_FILE_PATH")
    enable_logging(log_file_path)
    openai = OpenAI(openai_api_key)
    allowed_users = read_allowed_users()
    bot = ApplicationBuilder().token(telegram_token).concurrent_updates(True).build()
    bot.add_handlers(
        [
            CommandHandler("start", tele_start),
            CommandHandler("reset", tele_conversation_reset),
            CommandHandler("image", tele_image_creation),
            CommandHandler("transcribe", tele_audio_transcription),
            CommandHandler("help", tele_help),
            CommandHandler("adduser", tele_add_bot_user),
            CommandHandler("removeuser", tele_remove_bot_user),
            MessageHandler(filters.VOICE, tele_audio_recording_transcription),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
                tele_chat_completion,
            ),
            CallbackQueryHandler(remove_user),
        ]
    )
    try:
        print("Bot is running..")
        bot.run_polling()
    except Exception as e:
        logging.error(f"{e}")
        print("The bot has shut down due to an exception.")


if __name__ == "__main__":
    main()
