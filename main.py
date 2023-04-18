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
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")


def send_response(text, to_number, media_url=None):
    return twilio_client.messages.create(
        body=text,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        to=to_number,
        media_url=media_url
    )


@celery.task
def generate_response_chat(message_list, to_number, processing_message_sid):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                     {"role": "system",
                      "content": SYSTEM_PROMPT},
                 ] + message_list
    )

    response_text = response["choices"][0]["message"]["content"].strip()
    send_response(response_text, to_number, media_url="")

    # Delete the "Processing your request. Please wait..." message
    twilio_client.messages(processing_message_sid).delete()


def conversation_tracking(text_message, user_id, to_number, processing_message_sid):
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
    # Generate response
    task = generate_response_chat.apply_async(args=[conversation_history, to_number, processing_message_sid])

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


def save_voice_message_to_wav(media_content, filename):
    with open(filename + ".ogg", "wb") as f:
        f.write(media_content)

    sound = AudioSegment.from_file(filename + ".ogg", format="ogg")
    sound.export(filename + ".wav", format="wav")

    os.remove(filename + ".ogg")


@app.route("/chat", methods=["POST"])
@cross_origin()
def incoming_sms():
    # Get the incoming message from the request
    incoming_msg = request.values.get('Body', '').strip()
    mgs_form = request.values.get('From', '').strip()
    number = mgs_form[9:23]
    to_number = mgs_form
    voice = False
    new_response_text = ""
    other_response = False

    # Check if the message is a voice message
    if request.values.get("NumMedia") != "0":
        voice = True
        media_url = request.values.get("MediaUrl0")
        media_content = requests.get(media_url).content

        file_id = str(uuid.uuid4())
        wav_file_name = f"voice_message_{file_id}"

        save_voice_message_to_wav(media_content, wav_file_name)

        wav_file = wav_file_name + ".wav"

        r = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)

        text = text.lower()
        incoming_msg = text

    if incoming_msg.startswith("/start"):
        other_response = True
        new_response_text = "Hello, I am Sonic, your personal assistant. How can I help you today?\n1. /clear to " \
                            "clear old conversation"

    elif incoming_msg.startswith("/clear"):
        other_response = True
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
            processing_message = send_response("Processing your request. Please wait...", to_number)
            processing_message_sid = processing_message.sid
            conversation_tracking(incoming_msg, number, to_number, processing_message_sid)
        except Exception as e:
            my_error = str(e)
            print(my_error)
            send_response("Problem with fetch API or getting Data from Brain!", to_number)

    if voice:
        # Delete the temporary files
        os.remove(wav_file)

    if other_response:

        resp = MessagingResponse()
        resp.message(body=new_response_text)

        return str(resp)
    else:
        return '', 204


if __name__ == "__main__":
    app.run(debug=True)
