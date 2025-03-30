import requests
import PIL
import base64
import os
import traceback
from google import genai
from google.genai import types


# Dictionary to cache clients based on api_key
CLIENTS = {}

API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL_NAME = os.environ["GOOGLE_MODEL_NAME"]


def get_client(api_key=None):
    """Retrieve a Google GenAI client, caching clients by api_key."""
    key = api_key or "default"
    if key not in CLIENTS:
        CLIENTS[key] = genai.Client(api_key=api_key)
    return CLIENTS[key]


def get_response(
    conversation, conversation_with_metadata, model, api_key=None, mock7=False
):
    """Get response from Gemini API"""

    success7 = False
    if mock7:
        user_message = conversation[-1]["content"][0]["text"]
        res = f"User said: {user_message}"
        success7 = True
    else:
        try:
            client = get_client(api_key)

            # Prepare contents array by including the conversation history
            contents = []

            for message in conversation:
                # Determine the role of the message sender
                role = message.get("role", "user")  # Default to 'user' if not specified

                # Process each content part in the message
                content = message["content"]
                if isinstance(content, str):
                    # If content is a string, treat it as text content
                    contents.append(f"{role.capitalize()}: {content}")
                else:
                    # If content is an array of content parts
                    for content_part in content:
                        if content_part["type"] == "text":
                            # Prepend role to the message text
                            contents.append(
                                f"{role.capitalize()}: {content_part['text']}"
                            )
                        elif content_part["type"] == "image":
                            # Decode base64 image data to raw bytes
                            image_bytes = base64.b64decode(
                                content_part["source"]["data"]
                            )
                            # Create image part using Google's types
                            image_part = types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=content_part["source"]["media_type"],
                            )
                            contents.append(image_part)

            # Send the contents to Gemini
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=5000, temperature=1.0
                ),
            )

            res = response.text
            success7 = True

        except Exception as e:
            res = f"Google AI error: {e}"
            print(res)
            success7 = False
            # show full traceback
            traceback.print_exc()

    return res, success7


def ask_google(messages, max_length):
    res, success7 = get_response(
        messages, None, MODEL_NAME, api_key=API_KEY, mock7=False
    )
    return res
