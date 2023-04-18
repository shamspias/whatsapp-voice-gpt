# WhatsApp Voice GPT Chatbot: SonicAI

## Overview
SonicAI is built using Python, Flask, Twilio API, and OpenAI API. The chatbot utilizes asynchronous tasks with Celery to handle user requests and communicate with the OpenAI API efficiently. It supports both text and voice messages, allowing users to interact with the chatbot in their preferred format. The project is designed to be easily deployable and scalable, offering a seamless integration with WhatsApp.

## Features
- Engaging text-based conversations with GPT-3.5-turbo-powered AI
- Voice message recognition and processing
- Dynamic conversation tracking and history
- Supports commands to clear conversation history
- Utilizes asynchronous tasks with Celery for efficient request handling
- Built with Flask, Twilio API, and OpenAI API

## Installation
To set up SonicAI, follow the steps below:

1. Clone the repository:
```bash
git clone https://github.com/shamspias/whatsapp-voice-gpt.git 
```
2. Change into the project directory:
```bash
cd whatsapp-voice-gpt
```
3. Create a virtual environment:
```bash
python3 -m venv venv
```
4. Activate the virtual environment:
```bash
source venv/bin/activate
```
5. Install the dependencies and install redis-server:
```bash
pip install -r requirements.txt
```
6. Create a Twilio account and get your account SID and auth token. You can find the instructions [here](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account).
7. Create an OpenAI account and get your API key. You can find the instructions [here](https://beta.openai.com/docs/developer-quickstart/1-creating-an-api-key).
8. Create a `.env` file in the project directory and add the following environment variables or copy the contents of `.env.example` into the `.env` file:
```bash
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
OPEN_AI_KEY=your_openai_api_key
CELERY_BROKER_URL=your_celery_broker_url
CELERY_RESULT_BACKEND=your_celery_result_backend
SYSTEM_PROMPT=your_system_prompt
```
9. Run the celery worker:
```bash
celery -A app.celery worker --loglevel=info
```
10. Run the flask server:
```bash
python app.py
```
11. Expose the flask server to the internet using a tunneling service like [ngrok](https://ngrok.com/). You can find the instructions [here](https://www.twilio.com/docs/usage/tutorials/how-to-set-up-your-python-and-flask-development-environment#expose-your-application-to-the-internet).
12. Add the ngrok URL to your Twilio phone number's messaging webhook. You can find the instructions [here](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account#configure-your-twilio-phone-number).
13. Add the ngrok URL to your Twilio phone number's voice webhook. You can find the instructions [here](https://www.twilio.com/docs/voice/tutorials/how-to-receive-and-reply-inbound-phone-calls-python#configure-your-twilio-phone-number).
14. Send a WhatsApp message to your Twilio phone number to start a conversation with the chatbot.
15. Send a WhatsApp voice message to your Twilio phone number to start a voice conversation with the chatbot.
16. Send a WhatsApp message to your Twilio phone number with the command `/clear` to clear the conversation history.
17. Send a WhatsApp message to your Twilio phone number with the command `/help` to view the list of available commands.

## Contributing
Contributions are welcome! If you'd like to contribute, please submit a pull request or open an issue with your proposed changes or bug reports.
