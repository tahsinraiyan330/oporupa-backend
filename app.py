import os
import json
from flask import Flask, request, jsonify
from mistralai import Mistral
from flask_cors import CORS 

# --- Initialization ---
app = Flask(__name__)
# Enable CORS to allow your GitHub Pages site to talk to this server
CORS(app) 

# Retrieve the API Key and Agent ID from the environment variables (SECURE!)
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
OPORUPA_V1_AGENT_ID = os.environ.get("OPORUPA_V1_AGENT_ID")

# Initialize the Mistral Client
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

# A simple in-memory store to manage conversation IDs per session (basic state)
conversation_sessions = {}

# --- Helper Functions ---

def get_session_id():
    """Retrieves the session ID sent from the frontend to manage history."""
    # This uses the custom header defined in your frontend's script.js
    return request.headers.get('X-Session-ID', 'default_user')


# --- Server Routes ---

# 1. Health Check Route (FIXES THE 502 BAD GATEWAY ERROR)
@app.route('/', methods=['GET'])
def index():
    """Simple endpoint for Render health check and root URL access."""
    return jsonify({"status": "Oporupa V1 Backend is Live"}), 200


# 2. Main Chat API Endpoint
@app.route('/chat', methods=['POST'])
def chat():
    # 1. Check for server readiness
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
            )
            # Update the stored conversation ID (Mistral returns a new one on each append)
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
        bot_reply = "Oporupa V1 couldn't generate a definitive answer. Please try phrasing your legal question differently."
        if response.outputs and response.outputs[0].content:
            bot_reply = response.outputs[0].content

        return jsonify({"bot_response": bot_reply})

    except Exception as e:
        print(f"Mistral API Error: {e}")
        return jsonify({"bot_response": f"An unexpected error occurred while contacting Oporupa: {e}"}), 500

# For local testing, though Render uses Gunicorn
if __name__ == '__main__':
    app.run(debug=True)
