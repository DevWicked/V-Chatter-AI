from Assistant import Assistant

'''
Instructions

- Leave this code running whenever you want to utilize the chat feature. This is responsible for 
communicating with AI services and other types of APIs 

- Down below, insert your api keys and other info into the respective fields/variables. The values should be strings.
For example, if your api key or value for one of the info down below was apple, you would make it "apple"
'''

# used to generate AI response
OPENROUTER_KEY: str = ""
LLM_model: str = "google/gemini-2.0-flash-exp:free" # suggested 

'''
 this determines how much of the conversation the ai remembers. 
 default value is 5, so the ai remembers the past 5 exchanges
'''
context_limit: int = 5

# here you describe the personality of the AI or even try to have it roleplay as a character. I suggest testing this out on the OpenRouter website first
AI_personality: str = "" 

# [OPTIONAL]. used for text to speech. If api key is left empty as "" it wont attempt to get speech to text response
ELEVENLABS_API_KEY: str = ""
ELEVENLABS_VOICE_ID: str = ""

# [OPTIONAL]. used for speech to text. If api key is left empty as "" it wont attempt to get transcribe speech from user
ASSEMBLY_AI_KEY: str = ""

assistant = Assistant(OPENROUTER_KEY, LLM_model, context_limit, AI_personality, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ASSEMBLY_AI_KEY)
assistant.Start()

