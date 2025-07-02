import assemblyai as aai
from elevenlabs import ElevenLabs
from openai import OpenAI
from collections import deque
import re
import websockets
import asyncio
import time
from AiChatResponseObj import AiChatResponseObj
import json

class Assistant():

    """
    Class params almost all type string unless specified otherwise

    language_model_provider -> determines if you're using OpenAI or OpenRouter as your LLM service
    Openrouter_key-> api key for openrouter
    OpenAI_Key -> api key for openai
    Ollama_Port -> port number ollama server is running on
    llm_model-> specifies the llm name

    context_limit: integer -> the number of previous exchanges to remember in conversation. 
    ai_personality -> details how the model should behave
    ai_language -> determines the language your language model responds in. 
    allowedInactiveMinutes -> the number of minutes before the ai initiates a conversation due to chat inactivity

    elevenlabs_api_key -> api key for elevenlabs tts service
    elevenlabs_voice_id -> specifies the voice to use for the tts

    websocket_host -> the IP for your custom websocket server based AI backend (this program)
    websocket_port -> the port number for your custom websocket server based AI backend (this program)

    chat_data_save_folder -> where your chat info is stored (context, full history, ai tts file, user recording)

    """
    
    # set up class variables here to be used in functions this constructor is so freaking ugly
    def __init__(self, language_model_provider, OPENROUTER_KEY, OPENAI_KEY, Ollama_Port, LLM_model, context_limit, AI_personality, ai_language, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, websocket_host, websocket_port, chat_data_save_folder, allowedInactiveMinutes):
        
        self.chat_data_save_folder = chat_data_save_folder

        # LLM setup
        self.OPENROUTER_KEY = OPENROUTER_KEY 
        self.OPENAI_KEY = OPENAI_KEY
        llm_api_key = ""
        llm_base_url = ""

        if language_model_provider == 0: # OpenAI
            llm_api_key = OPENAI_KEY
            llm_base_url = "https://api.openai.com/v1"
        elif language_model_provider == 1: # OpenRouter
            llm_api_key = OPENROUTER_KEY
            llm_base_url = "https://openrouter.ai/api/v1"
        else: # Ollama
            llm_api_key = "ollama"
            llm_base_url = f"http://localhost:{Ollama_Port}/v1"

        self.LLM_Client = OpenAI(
            base_url= llm_base_url,
            api_key= llm_api_key
        )
        self.LLM_model = LLM_model

        self.context_limit = context_limit
        self.AI_Personality = AI_personality

        # configuration for AI initiated conversation 
        self.lastSentMessageTime = time.time()
        self.allowedInactiveMinutes = allowedInactiveMinutes


        # Elevenlabs (Text to speech)
        self.ELEVENLABS_API_KEY = ELEVENLABS_API_KEY 
        self.ELEVENLABS_VOICE_ID = ELEVENLABS_VOICE_ID
        self.ElevenLabsClient = ElevenLabs(
            api_key= ELEVENLABS_API_KEY,
        )


        # Open AI whisper (Speech to text)
        self.OpenAI_Whisper_Client = OpenAI(
            base_url= "https://api.openai.com/v1",
            api_key= OPENAI_KEY
        )
        

        # websocket configuration
        self.websocket_host = websocket_host
        self.websocket_port = websocket_port



        language_dictionary = { "en": "english", "es": "spanish", "ja": "japanese", "ko": "korean", "zh": "chinese"}
        # DO NOT CHANGE THE CONTENT OF PROMPT. THIS HELPS CREATE THE EXPRESSIONS ON MODEL
        self.prompt = {"role": "system", "content": "do not include descriptions, emojis, and actions. Keep responses on the shorter end. Always prepend each response with one corresponding sentiment." 
                        + "Your only sentiments are: neutral, annoyed, mad, happy, teasing, embarrassed and sarcastic. Enclose the sentiment with square brackets. An example is: " +
                        "[happy] Thank you for that compliment! The sentiment should always be in English, while the rest of the response should always be in " + 
                        language_dictionary[ai_language] + ". " + AI_personality}
        self.context = deque([self.prompt])



    # this is the actual function that gets called by main and initializes websocket communication that responds to request from unity app
    async def Start(self):

        # initialize context properly
        # skip over prompt when reading in context
        # TODO: check if file exists
        try:
            with open(self.chat_data_save_folder + '/chat_context.json', 'r') as file:
                data = json.load(file)
                onPrompt = True

                for message in data["messages"]:
                    if onPrompt: # dont readd prompt from context file to context in python script
                        onPrompt = False
                        continue

                    self.context.append(message)
        except FileNotFoundError:
            self.writeToContextFile()

        async with websockets.serve(self.handler, self.websocket_host, self.websocket_port, ping_interval=15, ping_timeout=5): # if dont get a response from client every 20 seconds, connection is closed from python persepctive

            print(f"WebSocket server started on ws://localhost:{self.websocket_port}")
            await asyncio.Future()  # run forever



    # for AI to message user when x minutes of chat inactivity occurs.
    async def PeriodicWebsocketMessageSender(self, websocket):
        while True:
            
            currentTime = time.time()
            if currentTime >= self.lastSentMessageTime + (self.allowedInactiveMinutes * 60):
                aiChatResponseObject = await self.handleTextMessageFromUser("(Giving you absolute directions. DO NOT MENTION ME GIVING YOU DIRECTIONS at all please) Send a message. It can be about the user not talking to you after a while (don't mention it being days), the current topic, or a new topic you want to talk about", 
                                                                            websocket, True)
                self.lastSentMessageTime = currentTime
                await websocket.send(json.dumps(aiChatResponseObject.__dict__))
                print("Max idle chat time hit")
            
            await asyncio.sleep(10) # sleep for 10 seconds



    async def handler(self, websocket):
        print("Client connected")

        # start the periodic sending background task
        backgroundMsgSenderTask = asyncio.create_task(self.PeriodicWebsocketMessageSender(websocket))

        try:
            async for message in websocket:
                print(f"Received from client: {message}")
                aiChatResponseObject = None

    
                if message == "*audio*" : # audio message sent by user
                    aiChatResponseObject = await self.handleVoiceMessageFromUser(websocket)

                elif message.startswith("*delete*"): # delete message from chat context request
                    messageId = message.split(" ")[1] # input would be "*delete* {messageId}". so this gives the message id
                    self.removeFromContext(messageId)
                    continue # finish this for loop iteration

                elif message.startswith("*clear context*"):
                    self.clearChatContext()
                    continue

                else: # text message sent by user
                    aiChatResponseObject = await self.handleTextMessageFromUser(message, websocket)

                # print(self.context)

                # Send to unity
                await websocket.send(json.dumps(aiChatResponseObject.__dict__)) # AiChatResponseObj type with tts enabled, sentiment, and ai open ai chat completion object
                
        except websockets.ConnectionClosed:
            print("Except block hit on websocket connection")

        finally:
            print("Finally block hit")
            print("Client disconnected")
            backgroundMsgSenderTask.cancel() # end the task



    '''
    
    HELPER FUNCTIONS DOWN BELOW
        
    '''

    # takes user text input or transcript from user voice input, then generates tts, then returns sentiment or "failed" (if something fails) for unity tcp client 
    async def handleTextMessageFromUser(self, message, websocket, aiInitiatedMessage = False):
        
        messageObject = {"role": "user", "content": ""} # for openAi
        messageObject["content"] = message
        messageObject["name"] = str(self.millisecondsSinceEpoch()) # give user message a message id

        if not aiInitiatedMessage: # if it's an actual user message
            userMessageChatResponseObject = AiChatResponseObj(messageObject)
            await websocket.send(json.dumps(userMessageChatResponseObject.__dict__)) # send user message back to client so can be added to chat history


        # generate AI response        
        response = self.generateResponse(messageObject)
        response = response.strip()
        sentiment = ""
        responseObject = {"role": "assistant", "content": response, "name": str(self.millisecondsSinceEpoch() + 1)} # give ai response a message id. need + 1 because get same value as user message

        # check to see if ai failed to generate a response
        if response == "":
            return AiChatResponseObj(sentiment="failed")
        

        # extract sentiment and remove from response
        regexSearchObject = re.search("\[\w+\]", response)
        if response.startswith("[") and regexSearchObject != None:
            sentiment = self.extractSentiment(regexSearchObject.group())
            print(f"Extracted sentiment: {sentiment}")
            startIndex = response.index("]") + 1
            response = response[startIndex:].strip()
        else:
            print("No sentiment was included in ai response so set to neutral")
            sentiment = "neutral" # default value if no sentiment was included 
        
        print(f"AI generated response: {response}\n")
    
        # Add exchange to context
        self.updateContext(messageObject, responseObject)

        # remove user message that asks ai to initate convo with user if this should've been initiated by AI
        if aiInitiatedMessage:
            self.removeFromContext(messageObject["name"])
        
        # generate ai tts if able to
        ttsEnabled = self.generateTtsMP3(response) 
        
        # reset inactivity timer
        self.lastSentMessageTime = time.time()

        return AiChatResponseObj(aiResponse= responseObject, ttsEnabled= ttsEnabled, sentiment= sentiment)

    

    # get the sentiment from AI response by getting substring (if exists) prepended to the content
    def extractSentiment(self, string):
        return string[1:-1]



    # update the context containing past messages of conversation for AI. Param message is user message
    def updateContext(self, message, response):
        # do these first in case user wants 0 context (leaving only the prompt)
        self.context.append(message)
        self.context.append(response)
        prompt = self.context.popleft()

        # if past length limit, pop oldest exchange/message from context
        if (len(self.context) - 1) / 2 > self.context_limit:
            self.context.popleft(); # pop oldest message from context 
        
        self.context.appendleft(prompt) # readd the prompt as it was popped earlier
        self.writeToContextFile()

    

    def removeFromContext(self, messageId):
        indexToRemove = -1
        index = 0

        for message in self.context:
            if "name" in message and message["name"] == messageId:
                indexToRemove = index 
                break
            index += 1
        
        print("Deleted index " + str(indexToRemove))

        if indexToRemove != -1:
            del self.context[indexToRemove]

        self.writeToContextFile()



    def clearChatContext(self):
        self.context = deque([self.prompt])
        self.writeToContextFile()



    def writeToContextFile(self):
        with open(self.chat_data_save_folder + '/chat_context.json', 'w') as f: # text mode, not 'wb'
            json.dump({"messages" : list(self.context)}, f)       



    # get transcript of voice input audio and feed transcript to text message handler
    async def handleVoiceMessageFromUser(self, websocket):
        speechText = self.transcribeUserSpeech()
        
        # if speech to text api failed or user was muted (or didn't say anything), no response to generate and ultimately no sentiment to return
        if speechText == "*failed*" or speechText.isspace():
            return AiChatResponseObj(sentiment="failed")

        print(f"Audio transcribed as: {speechText}")

        # return object from function
        return await self.handleTextMessageFromUser(speechText, websocket)
    


    def millisecondsSinceEpoch(self):
        return int(round(time.time() * 1000))
    


    '''
    These are the functions you can customize to use any AI service, local model, and local software you want! 
    You can alter the LLM function, the TTS function, and the speech to text function
    Just make sure the return types match!
    '''


    # generate AI response to user. return response message object (used by GPT library) and the actual text of response
    # when you send the message to AI, remove the name that contains the time stamp since it messes it up
    # "LLM Function"
    def generateResponse(self, message:dict[str, str]):
        try:
            contextWithoutNameProp = [ {k: v for k, v in contextMessage.items() if k != "name"} for contextMessage in self.context ]
            messageWithoutNameProp = {k: v for k, v in message.items() if k != "name"}
            
            completion = self.LLM_Client.chat.completions.create(
                model= self.LLM_model,
                messages= [*contextWithoutNameProp, messageWithoutNameProp] # new message would be appended at end here
            )

            return completion.choices[0].message.content

        except Exception as err:
            print("Failed to generate ai response \n")
            print(err)
            return ""
    


    # turn AI generated response to mp3. returns true if successfully done, else false
    # "TTS Function"
    def generateTtsMP3(self, message:str):
        if self.ELEVENLABS_API_KEY == "":
            return False 
        
        try:
            audio_data = self.ElevenLabsClient.text_to_speech.convert(
                voice_id= self.ELEVENLABS_VOICE_ID,
                output_format= "mp3_44100_128",
                text= message,
                model_id= "eleven_flash_v2_5", # Faster output than eleven_multilingual_v2 and use less credits
            )

            with open(self.chat_data_save_folder + "/generated_audio.mp3", 'wb') as file:
                for chunk in audio_data:
                    file.write(chunk)
            
            return True

        except Exception as err:
            print("Failed to generate tts mp3 file for ai response \n")
            print(err)
            return False
        

    # turn user recorded speech into text for LLM to respond to. If fails, return *failed*
    # "Speech to text function"
    def transcribeUserSpeech(self):
        try:
            audio_file = open(self.chat_data_save_folder + "/user_recording.wav", "rb")
            speechText = self.OpenAI_Whisper_Client.audio.transcriptions.create(model="whisper-1", file=audio_file,)
            return speechText.text

        except Exception as e:
            print(e)
            print("Failed to transcribe user voice input \n")
            return "*failed*" # need this since person can just say failed and have it transcripted
    