# Sticker pack manager
This is a python project meant to make organizing telegram stickers much easier.
It allows to save sticker packs sent to a bot, then, with a web UI, you can delete them and
create custom sticker packs out of them.

---

## Installation:
1. Create a python virtual environment
```sh
python -m venv .venv
```

2. Install the requirements
```sh
pip install -r requirements.txt
```

3. Enter the environment
```sh
source .venv/bin/activate
```

4. Set up environment variables  
To use this application you need to create a .env file with the following variables:
- `BOT_TOKEN`: is a Telegram bot token, acquired via BotFather on Telegram.
- `SIGNAL_UUID`: it's Signal messenger's UUID.
- `SIGNAL_PASSWORD`: it's Signal messenger's UUID.  
Both Signal messenger's variables are required to upload a sticker pack to signal.
To get those variables you need to do the following steps on Signal desktop:
1. Run signal using the `--enable-dev-tools` flag.
2. Open the developer tools (View -> Toggle Developer Tools).
3. Navigate to the console in the developer tools.
4. Change context from Top to Electron Isolated Context.
5. Run `window.reduxStore.getState().items.uuid_id` to get the UUID.
6. Run `window.reduxStore.getState().items.password` to get the PASSWORD.

---

## Usage:
To use the scripts there are two main files:
```sh
# To run telegram bot
python -m src.bot.main
# To run web application
python -m src.web.main
```

---

## TO-DO List:
- Fix custom packs:
    - Loading the individual stickers section takes a while as scroll pagination seems not to work (it loads all stickers right away).
