from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import speech_recognition as sr
from pydub import AudioSegment
from flask import Flask, request
from dotenv import load_dotenv
from flask_cors import cross_origin
from celery import Celery
import requests
import openai
import os
import uuid

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Initialize Celery
celery = Celery(app.name, broker=os.getenv('CELERY_BROKER_URL'))
celery.conf.update(result_backend=os.getenv('CELERY_RESULT_BACKEND'), task_serializer='json', result_serializer='json',
                   accept_content=['json'])

# Initialize the OpenAI API
openai.api_key = os.getenv("OPEN_AI_KEY")

# Store the last 10 conversations for each user
conversations = {}

# Initialize the Twilio API


# Your Account SID and Auth Token from twilio.com/console
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")


@celery.task
def generate_response_chat(message_list):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                     {"role": "system",
                      "content": SYSTEM_PROMPT},
                 ] + message_list
    )
    print(response)

    return response["choices"][0]["message"]["content"].strip()


def conversation_tracking(text_message, user_id):
    """
    Make remember all the conversation
    :param old_model: Open AI model
    :param user_id: telegram user id
    :param text_message: text message
    :return: str
    """
    # Get the last 10 conversations and responses for this user
    user_conversations = conversations.get(user_id, {'conversations': [], 'responses': []})
    user_messages = user_conversations['conversations'][-9:] + [text_message]
    user_responses = user_conversations['responses'][-9:]

    # Store the updated conversations and responses for this user
    conversations[user_id] = {'conversations': user_messages, 'responses': user_responses}

    # Construct the full conversation history in the user:assistant, " format
    conversation_history = []

    for i in range(min(len(user_messages), len(user_responses))):
        conversation_history.append({
            "role": "user", "content": user_messages[i]
        })
        conversation_history.append({
            "role": "assistant", "content": user_responses[i]
        })

    # Add last prompt
    conversation_history.append({
        "role": "user", "content": text_message
    })
    # Generate response
    task = generate_response_chat.apply_async(args=[conversation_history])
    response = task.get()

    # Add the response to the user's responses
    user_responses.append(response)

    # Store the updated conversations and responses for this user
    conversations[user_id] = {'conversations': user_messages, 'responses': user_responses}

    return response


def clear_conversation_history(user_id):
    """
    Clear the conversation history for a specific user
    :param user_id: user id
    :return: None
    """
    if user_id in conversations:
        conversations[user_id] = {'conversations': [], 'responses': []}
        return True
    return False


@app.route("/chat", methods=["POST"])
@cross_origin()
def incoming_sms():
    # Get the incoming message from the request
    incoming_msg = request.values.get('Body', '').strip()
    mgs_form = request.values.get('From', '').strip()
    number = mgs_form[9:23]
    voice = False

    # Check if the message is a voice message
    if request.values.get("NumMedia") != "0":
        voice = True
        media_url = request.values.get("MediaUrl0")
        media_content = requests.get(media_url).content

        # Use the Via API to convert the voice message to text
        # Save the file to disk
        with open("voice_message.ogg", "wb") as f:
            f.write(media_content)

        # Use pydub to read in the audio file and convert it to WAV format
        sound = AudioSegment.from_file("voice_message.ogg", format="ogg")
        sound.export("voice_message.wav", format="wav")

        # Use SpeechRecognition to transcribe the voice message
        r = sr.Recognizer()
        with sr.AudioFile("voice_message.wav") as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)

        text = text.lower()
        incoming_msg = text

    if incoming_msg.startswith("/start"):
        new_response_text = "Hello, I am Sonic, your personal assistant. How can I help you today?\n1. /clear to " \
                            "clear old conversation"

    elif incoming_msg.startswith("/clear"):
        try:
            user_id = number
            if clear_conversation_history(user_id):
                new_response_text = "Your chat thread has now been reset. What else can I assist you with today?"
            else:
                new_response_text = "No conversation history to clear. What else can I assist you with today?"
        except Exception as e:
            my_error = str(e)
            print(my_error)
            new_response_text = "Can't Delete Conversation"

    else:

        try:
            response_text = conversation_tracking(incoming_msg, number)
            new_response_text = response_text

        except Exception as e:
            my_error = str(e)
            print(my_error)
            response_text = "Problem with fetch API or getting Data from Brain!"
            new_response_text = response_text

    if voice:
        file_id = str(uuid.uuid4())
        ogg_file = f"voice_message_{file_id}.ogg"
        wav_file = f"voice_message_{file_id}.wav"
        mp4_file = f"voice_message_{file_id}.mp4"

        with open(ogg_file, "wb") as f:
            f.write(media_content)

        sound = AudioSegment.from_file(ogg_file, format="ogg")
        sound.export(wav_file, format="wav")

        # ... (previous code)

        # Convert the voice message to .mp4 format
        sound = AudioSegment.from_file(ogg_file, format="ogg")
        sound.export(mp4_file, format="mp4")

        resp = MessagingResponse()
        resp.message(body=new_response_text, media=mp4_file)
        # resp.message(new_response_text).media(mp4_file)

        # Delete the temporary files
        os.remove(ogg_file)
        os.remove(wav_file)
        os.remove(mp4_file)

        return str(resp)


if __name__ == "__main__":
    app.run(debug=True)
