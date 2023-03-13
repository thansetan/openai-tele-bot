# A Telegram bot that connects to OpenAI's API

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

## You can also deploy this bot on [Streamlit](https://share.streamlit.io/)
To do that, you need to create a [secrets](https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management) using [TOML](https://toml.io/en/latest) format first. Here's an example:

```
OPENAI_API_KEY = "<your-openai-API-key>"
TELEGRAM_BOT_TOKEN = "<your-Telegram-bot-token>"
INITIAL_USER_ID = "<your-Telegram-user-id>"
LOG_FILE_PATH = "<your-desired-log-file-path>"
```

In this case, you don't need to edit the `.env` file.

## Important Command
1. `/addsuser <username>` -- **Admin Only**
2. `/removeuser` -- **Admin Only**
