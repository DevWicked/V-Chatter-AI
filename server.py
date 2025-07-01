from Assistant import Assistant
import asyncio

'''
Instructions
- Down below, follow the instructions for each section and fill out each field

- To run this file, make sure to open up your terminal (command prompt) inside this folder and then run the command: python server.py

- Leave this code running whenever you want to utilize the chat feature for the Steam release or if you want to fully customize the AI aspect
'''

# [OPTIONAL] You don't need to change any of these values in this section. If you know what you're doing, feel free to change --------------------------------------

websocket_host: str = "127.0.0.1" # local host
websocket_port: int = 8765

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------



# Chat data save folder [MANDATORY] -------------------------------------------------------------------------------------------------------------------------------

# use this folder by default. you can create a new folder where you wish for your chat data to be saved to, and then paste its location (Path) here
# MAKE SURE it's the same folder that's selected for your chat date save folder in the v-chatter app (settings -> chat)
chat_data_save_folder: str = "./" 

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------



# Language Model Section [MANDATORY] ------------------------------------------------------------------------------------------------------------------------------

# Choose if you're using OpenAI or OpenRouter for the language model service. OpenAI = 0, OpenRouter = 1
language_model_provider : int = 0

# you need to fill this out if you chose open ai for the language model provider and/or if you want speech to text
OPENAI_KEY: str = ""

# you need to fill this out if you chose open router for the lanuage model provider
OPENROUTER_KEY: str = ""

# specify the name of the language model you're using
language_model_name: str = "" 

# this determines how much of the conversation the ai remembers.  default value is 5, so the ai remembers the past 5 exchanges. A user message and ai response counts as 1 exchange
context_limit: int = 5

# here you describe the personality of the AI or even try to have it roleplay as a character.
AI_personality: str = "" 

# the number of inactive minutes allowed in chat before the AI initiates a conversation
allowed_inactive_minutes: int = 5

# the language the AI responds in. Allowed values: en (english), es (spanish), ja (japanese), ko (korean), zh (chinese). 
ai_language: str = "en" # default

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------



# Text to Speech Section [OPTIONAL]. If api key is left empty as "", it wont attempt to get text to speech response -----------------------------------------------

ELEVENLABS_API_KEY: str = ""
ELEVENLABS_VOICE_ID: str = ""

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------



# Speech to Text Section [OPTIONAL]. If OpenAI api key is left empty as "" it wont attempt to get transcribe speech from user -------------------------------------------

# PLEASE fill in the OpenAI key in the Language Model Section if you wish to have speech to text!

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------



# don't touch this
assistant = Assistant(language_model_provider, OPENROUTER_KEY, OPENAI_KEY, language_model_name, context_limit, AI_personality, ai_language, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, websocket_host, websocket_port, chat_data_save_folder, allowed_inactive_minutes)
asyncio.run(assistant.Start())

