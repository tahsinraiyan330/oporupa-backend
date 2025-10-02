import os
import json
from flask import Flask, request, jsonify
from mistralai import Mistral
from flask_cors import CORS # Required to allow requests from your GitHub Pages domain

# --- Initialization ---
app = Flask(__name__)
# Enable CORS for all routes, allowing your GitHub Pages site to talk to this server
CORS(app)

# Retrieve the API Key from the environment variables (REQUIRED FOR SECURITY!)
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
OPORUPA_V1_AGENT_ID = os.environ.get("OPORUPA_V1_AGENT_ID")

# Initialize the Mistral Client
# It will automatically use the MISTRAL_API_KEY from the environment
if MISTRAL_API_KEY:
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        print("Mistral Client Initialized Successfully.")
    except Exception as e:
        print(f"Error initializing Mistral Client: {e}")
        client = None
else:
    print("MISTRAL_API_KEY not found. API calls will fail.")
    client = None

# A simple in-memory store to manage conversation IDs per session (basic approach)
conversation_sessions = {}

# --- Helper Functions ---

def get_session_id():
    """Generates a simple session ID or uses one from the request."""
    # This is a simple way; for production, you'd use cookies or JWTs.
    return request.headers.get('X-Session-ID', 'default_user')


# --- API Endpoint ---

@app.route('/chat', methods=['POST'])
def chat():
    # 1. Check client
    if not client or not OPORUPA_V1_AGENT_ID:
        return jsonify({"bot_response": "Server error: AI Agent is not configured. Contact the developer."}), 503

    # 2. Get user message and session ID
    data = request.json
    user_message = data.get('message')
    session_id = get_session_id()
    
    if not user_message:
        return jsonify({"bot_response": "No message provided."}), 400

    try:
        # 3. Handle Conversation Logic (Start or Append)
        conversation_id = conversation_sessions.get(session_id)
        
        if conversation_id:
            # Continue an existing conversation
            response = client.beta.conversations.append(
                conversation_id=conversation_id,
                inputs=user_message,
                # Set store=True to maintain history for the agent (this is the default)
            )
            # Mistral returns a new conversation ID on each append, so update the session
            conversation_sessions[session_id] = response.conversation_id
            
        else:
            # Start a new conversation
            response = client.beta.conversations.start(
                agent_id=OPORUPA_V1_AGENT_ID,
                inputs=user_message,
            )
            # Store the new conversation ID for this session
            conversation_sessions[session_id] = response.conversation_id

        # 4. Extract Bot Response
        # The content of the bot's reply is in the 'outputs' array
        bot_reply = "Sorry, I couldn't get a response from Oporupa_V1."
        if response.outputs and response.outputs[0].content:
            bot_reply = response.outputs[0].content

        return jsonify({"bot_response": bot_reply})

    except Exception as e:
        print(f"Mistral API Error: {e}")
        return jsonify({"bot_response": f"An unexpected error occurred while contacting Oporupa: {e}"}), 500

# For Render deployment, we need a simple entry point
if __name__ == '__main__':
    app.run(debug=True)
