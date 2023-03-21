import logging
import os
from tempfile import TemporaryDirectory

import openai
from dotenv import load_dotenv
from pydub import AudioSegment
from revChatGPT.V3 import Chatbot
from telegram import (ChatAction, InlineKeyboardButton, InlineKeyboardMarkup,
                      InputMediaPhoto)
from telegram.error import BadRequest
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)

load_dotenv()  # load .env file


# OpenAI
def authenticate(api_key):
    openai.api_key = api_key
    chatbot = Chatbot(api_key=api_key, temperature=0.7)
    return chatbot


def chat_completion(message, convo_id):
    completion = chatbot.ask(
        prompt=message,
        convo_id=convo_id,
    )
    return completion


def generate_image(prompt):
    image = openai.Image.create(prompt=prompt, n=2, size="1024x1024")
    return image.get("data")


def transcribe(audio):
    audio = open(audio, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio).get("text")
    return transcript


# Telegram
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


def set_typing(context, effective_chat_id):
    context.bot.send_chat_action(chat_id=effective_chat_id, action=ChatAction.TYPING)


def start(update, context):
    message_text = "🤖 This bot is connected to OpenAI's API. To get an idea of what this bot is capable of, type /help."
    convo_id = update.message.from_user.id
    if convo_id in chatbot.conversation.keys():
        chatbot.reset(convo_id)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=message_text, parse_mode="markdown"
    )


def tele_chat_completion(update, context):
    convo_id = update.message.from_user.id
    if last_msg_time.get(convo_id):
        time_diff = update.message.date - last_msg_time[convo_id]
        if time_diff.total_seconds() / 3600 > 3:
            chatbot.reset(convo_id)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⌛ Our conversation has been reset due to inactivity.",
            )
    set_typing(context, update.effective_chat.id)
    last_msg_time[convo_id] = update.message.date
    if not_allowed(update):
        text = bot_not_allowed
    else:
        prompt = update.message.text
        chatbot.conversation.setdefault(convo_id, [])
        response = chat_completion(prompt, convo_id)
        chatbot.add_to_conversation(prompt, "user", convo_id)
        text = response
    try:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            parse_mode="markdown",
        )
    except BadRequest as e:
        logging.error(f"Can't send message using markdown: {e}")
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def tele_chat_reset_conversation(update, context):
    convo_id = update.message.from_user.id

    if convo_id not in chatbot.conversation:
        if not_allowed(update):
            text = [bot_not_allowed]
        else:
            text = [
                "😡 This is our first conversation, what do you want to reset you stoopid?"
            ]
    else:
        chatbot.reset(convo_id)
        last_msg_time.pop(convo_id, None)
        text = [
            "🤓 Our conversation has been reset, and now it's like we're two people who have just met and don't know each other yet.",
            "🤖 Hi, I'm ChatGPT. What can I do to help you?",
        ]
    for t in text:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=t,
        )


def tele_image_creation(update, context):
    message = update.message

    set_typing(context, update.effective_chat.id)
    if not_allowed(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=bot_not_allowed,
            parse_mode="markdown",
        )
    else:
        message_content = message.text.split(" ", 1)
        if len(message_content) > 1:
            prompt = message_content[1]
            images = generate_image(prompt)
            image_list = [
                InputMediaPhoto(
                    media=data.get("url"), caption=f"🧑🏽‍🎨 image no {i} of {prompt}"
                )
                for i, data in enumerate(images, start=1)
            ]
            context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=image_list,
                reply_to_message_id=message.message_id,
            )
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🥺 Please enter the prompt (`/image <your-prompt-here>`)",
                reply_to_message_id=message.message_id,
                parse_mode="markdown",
            )


def tele_audio_transcribe(update, context):
    allowed_files = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    is_reply = False
    max_file_size = 26214400
    message = update.message

    set_typing(context, update.effective_chat.id)
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
            file_extension = file.file_path.split(".")[-1]
            if file_extension in allowed_files:
                file_id = file.file_id
                file_name = f"{file_id}.{file_extension}"
                text = temp_save_and_transcribe(file, file_name)
            else:
                text = "😔 File not allowed"
        else:
            text = "😔 Invalid quoted message"
        if file_size and file_size > max_file_size:
            text = "⚠️ File size can't be more than 25 MB."
    else:
        text = "📎 To use this command, you need to reply/quote a file."
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_to_message_id=quoted_message if is_reply else message.message_id,
    )


def tele_audio_recording_transcribe(update, context):
    set_typing(context, update.effective_chat.id)
    file_id = update.message.voice.file_id
    if not_allowed(update):
        text = bot_not_allowed
    else:
        file = context.bot.get_file(file_id)
        file_name = f"{file_id}.ogg"
        text = temp_save_and_transcribe(file, file_name, True)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def tele_help(update, context):
    set_typing(context, update.effective_chat.id)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=help_message, parse_mode="markdown"
    )


def tele_add_bot_user(update, context):
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
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=text, parse_mode="markdown"
    )


def remove_user(update, context):
    query = update.callback_query
    if query.data == "cancel":
        query.edit_message_text(text="❌ Aborting request.")
        query.message.delete()
    else:
        user_id = query.data
        username = allowed_users[int(user_id) - 1]
        query.answer()
        allowed_users.remove(username)
        with open("allowed_users.txt", "w") as f:
            f.write("\n".join([user for user in allowed_users]))
        query.edit_message_text(
            text=f"🗑️ {username} has been removed and can no longer use this bot."
        )


def tele_remove_bot_user(update, context):
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
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup if can_remove else None,
    )


# Other
def enable_logging(log_file_path):
    if log_file_path:
        if not os.path.exists(log_file_path):
            open(log_file_path, "a").close()
        logging.basicConfig(
            filename="bot.log",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.ERROR,
        )


def temp_save_and_transcribe(file, file_name, is_voice_message=False):
    with TemporaryDirectory() as tmp_dir:
        tmp_file_path = os.path.join(tmp_dir, file_name)
        file.download(tmp_file_path)
        if is_voice_message:
            tmp_mp3_path = os.path.splitext(tmp_file_path)[0] + ".mp3"
            AudioSegment.from_file(tmp_file_path, format="ogg").export(
                tmp_mp3_path, format="mp3"
            )
            tmp_file_path = tmp_mp3_path
        transcript = transcribe(tmp_file_path)
    return transcript


def read_allowed_users():
    allowed_users = []
    with open("allowed_users.txt", "a+"):
        pass
    with open("allowed_users.txt", "r") as f:
        allowed_users = [user.strip() for user in f.readlines()]
    return allowed_users


def main():
    global chatbot, initial_user, allowed_users
    openai_api_key = os.getenv("OPENAI_API_KEY")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    log_file_path = os.getenv("LOG_FILE_PATH")
    initial_user = int(os.getenv("INITIAL_USER_ID"))
    enable_logging(log_file_path)
    chatbot = authenticate(openai_api_key)
    allowed_users = read_allowed_users()
    updater = Updater(token=telegram_bot_token)
    app = updater.dispatcher
    start_handler = CommandHandler("start", start)
    chat_completion_handler = MessageHandler(
        Filters.text & ~Filters.command & ~Filters.update.edited_message,
        tele_chat_completion,
    )
    reset_handler = CommandHandler("reset", tele_chat_reset_conversation)
    image_creation_handler = CommandHandler("image", tele_image_creation)
    transcribe_handler = CommandHandler("transcribe", tele_audio_transcribe)
    transcribe_from_audio_msg_handler = MessageHandler(
        Filters.voice, tele_audio_recording_transcribe
    )
    add_user_handler = CommandHandler("adduser", tele_add_bot_user)
    remove_user_handler = CommandHandler("removeuser", tele_remove_bot_user)
    remove_button_handler = CallbackQueryHandler(remove_user)
    help_handler = CommandHandler("help", tele_help)
    handler_list = [
        start_handler,
        add_user_handler,
        remove_user_handler,
        remove_button_handler,
        chat_completion_handler,
        reset_handler,
        image_creation_handler,
        transcribe_handler,
        transcribe_from_audio_msg_handler,
        help_handler,
    ]
    for handler in handler_list:
        app.add_handler(handler)
    try:
        print("Bot has started.")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logging.error(f"{e}")
        print("The bot has shut down due to an exception.")


if __name__ == "__main__":
    main()
