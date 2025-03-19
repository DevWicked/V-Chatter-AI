import socket
import assemblyai as aai
from elevenlabs import ElevenLabs
from openai import OpenAI
from collections import deque
import re

class Assistant():

    """
    Class params almost all type string unless specified otherwise

    Openrouter_key-> api key for openrouter
    llm_model-> specifies the llm used in openrouter

    context_limit: integer -> the number of previous messages to remember in conversation. should always be at least 1 so it at least remembers prompt
    ai_personality -> details how the model should speak 

    elevenlabs_api_key -> api key for elevenlabs tts service
    elevenlabs_voice_id -> specifies the voice to use for the tts

    assembly_ai_key -> api key for assemble ai which is currently used for speech to text
    """
    
    # set up class variables here to be used in functions
    def __init__(self, OPENROUTER_KEY, LLM_model, context_limit, AI_personality, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ASSEMBLY_AI_KEY):
        
        # Open Router (LLM)
        self.OPENROUTER_KEY = OPENROUTER_KEY 
        self.openRouterClient = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_KEY
        )
        self.LLM_model = LLM_model

        self.context_limit = context_limit
        self.AI_Personality = AI_personality

        # Elevenlabs (Text to speech)
        self.ELEVENLABS_API_KEY = ELEVENLABS_API_KEY 
        self.ELEVENLABS_VOICE_ID = ELEVENLABS_VOICE_ID
        self.ElevenLabsClient = ElevenLabs(
            api_key= ELEVENLABS_API_KEY,
        )


        # Assembly AI (Speech to text)
        self.ASSEMBLY_AI_KEY = ASSEMBLY_AI_KEY
        aai.settings.api_key = self.ASSEMBLY_AI_KEY if self.ASSEMBLY_AI_KEY != "" else "dummy" # need to provide non empty string 
        self.transcriber = aai.Transcriber()
        
        # DO NOT CHANGE THE CONTENT. THIS HELPS CREATE THE EXPRESSIONS ON MODEL
        self.context = deque([{"role": "system", "content": "do not include descriptions, emojis, and actions. Keep responses on the shorter end. Always prepend each response with one corresponding sentiment." 
                        + "Your only sentiments are: neutral, annoyed, mad, happy, teasing, and sarcastic. Enclose the sentiment with square brackets. An example is: " +
                        "[happy] Thank you for that compliment! " + AI_personality}])
    


    # this is the actual function that gets called by main and generates a TCP server that responds to request from unity app
    def Start(self):
        host: str = "127.0.0.1" # localhost
        port = 25001

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP socket
        server_socket.bind((host, port))

        # Start listening for incoming connections. 3 is arbitrary
        server_socket.listen(3)
        print(f"Server listening on {host}:{port}")

        while True:
            # Accept a connection from a client
            client_socket, client_address = server_socket.accept()
            print(f"Connection established")

            # Receive data from the client
            data = client_socket.recv(1024)  # Buffer size of 1024 bytes
            message = data.decode()
            sentiment = ""

            print(f"User sending message: {message}")

            # text message sent by user
            if message != "*audio*" :
                sentiment = self.handleTextMessageFromUser(message)
            else: # audio message
                sentiment = self.handleVoiceMessageFromUser()

            # Send to unity the sentiment upon success and "failed" upon failure
            message = f"{sentiment} no stt" if self.ELEVENLABS_API_KEY == "" else sentiment
            client_socket.send(message.encode())



    '''
    
    HELPER FUNCTIONS DOWN BELOW
        
    '''

    # takes user text input or transcript from user voice input, then generates tts, then returns sentiment or "failed" (if something fails) for unity tcp client 
    def handleTextMessageFromUser(self, message):
        messageObject = {"role": "user", "content": ""} # for openAi
        
        messageObject["content"] = message
        responseObject, response = self.generateResponse(messageObject)
        response = response.strip()
        sentiment = ""

        if responseObject == None or response == "":
            return "failed"

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
        
        print(f"Received message: {response}\n")
    
        # once done generating a response, add dialogue to context and generate corresponding audio
        self.updateContext(messageObject, responseObject)
        if self.ELEVENLABS_API_KEY != "" and not self.generateTtsMP3(response):
            return "failed" # failed to generate tts mp3
        
        return sentiment

    

    # get the sentiment from AI response by getting substring (if exists) prepended to the content
    def extractSentiment(self, string):
        return string[1:-1]



    # generate AI response to user. return response message object (used by GPT library) and the actual text of response
    def generateResponse(self, message:dict[str, str]):
        try:
            completion = self.openRouterClient.chat.completions.create(
                model= self.LLM_model,
                messages= [*self.context, message] # new message would be appended at end here
            )

            return [completion.choices[0].message, completion.choices[0].message.content]
        
        except:
            print("Failed to generate ai response \n")
            return[None, ""]
    


    # turn AI generated response to mp3. returns true if successfully done, else false
    def generateTtsMP3(self, message:str):
        try:
            audio_data = self.ElevenLabsClient.text_to_speech.convert(
                voice_id= self.ELEVENLABS_VOICE_ID,
                output_format= "mp3_44100_128",
                text= message,
                model_id= "eleven_flash_v2_5", # Faster output than eleven_multilingual_v2 and use less credits
            )

            with open("generated_audio.mp3", 'wb') as file:
                for chunk in audio_data:
                    file.write(chunk)
            
            return True
        
        except:
            print("Failed to generate tts mp3 file for ai response \n")
            return False



    # update the context containing past messages of conversation for AI. Param message is user message
    def updateContext(self, message, response):

        # should be at context_limit + 2 due to user message and response
        # if past length limit, pop oldest exchange from context
        if len(self.context) > self.context_limit:
            prompt = self.context.popleft()
            self.context.popleft(); self.context.popleft(); # pop oldest exchange from context 
            self.context.appendleft(prompt) # readd the prompt as it was popped earlier
        
        self.context.append(message)
        self.context.append(response)
        


    # get transcript of voice input audio and feed transcript to text message handler
    def handleVoiceMessageFromUser(self):
        speechText = self.transcribeUserSpeech("./user_recording.wav")
        
        # if speech to text api failed or user was muted (or didn't say anything), no response to generate and ultimately no sentiment to return
        if speechText == "*failed*" or speechText.isspace():
            return "failed"

        print(f"Audio transcribed as: {speechText}")

        # return sentiment from function
        return self.handleTextMessageFromUser(speechText)
    


    # turn user recorded speech into text for LLM to respond to
    def transcribeUserSpeech(self, filePath):
        try:
            speechText = self.transcriber.transcribe(filePath)
            return speechText.text
        
        except:
            print("Failed to transcribe user voice input \n")
            return "*failed*" # need this since person can just say failed and have it transcripted
    