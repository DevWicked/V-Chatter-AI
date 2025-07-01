from openai import OpenAI

class AiChatResponseObj():
    def __init__(self, userMessage = None, aiResponse = None, ttsEnabled:bool = False, sentiment: str = ""):
        self.userMessage = userMessage
        self.aiResponse = aiResponse
        self.ttsEnabled = ttsEnabled
        self.sentiment = sentiment

