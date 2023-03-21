# A Telegram bot that connects to OpenAI's API (Async Version)

> Unlike the synchronous version, in this asynchronous version, the bot will directly process any request from different users without waiting for a previous request to be completed.
<br>In the synchronous version, if two users (let's say A and B) send messages at the same time, the bot will wait for A's request to be completed before processing B's request.
<br>In this asynchronous version, the bot will process the requests simultaneously.

## How to use
To use this bot, follow these steps:

1. Clone the repository.
2. (Optional) Create a virtual environment.
3. Install dependencies using either `pip install -r requirements.txt` or `conda install --file requirements.txt`.
4. Rename `.env.example` to `.env` and enter your:
    - `OPENAI_API_KEY` = Your [OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key),
    - `TELEGRAM_BOT_TOKEN` = Your [Telegram bot token](https://medium.com/geekculture/generate-telegram-token-for-bot-api-d26faf9bf064),
    - `INITIAL_USER_ID` = Your Telegram [user ID](https://bigone.zendesk.com/hc/en-us/articles/360008014894-How-to-get-the-Telegram-user-ID-) -- **this will be treated as an admin**,
    - and `LOG_FILE_PATH` = your desired log file path -- **(optional)**.
    
    and save.
5. Run the bot using `python main.py`.

## Important Command
1. `/addsuser <username>` -- **Admin Only**
2. `/removeuser` -- **Admin Only**
