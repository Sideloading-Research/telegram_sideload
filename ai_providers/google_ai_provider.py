import requests
import PIL
import base64
import os
import traceback
from google import genai
from google.genai import types
from google.genai import errors
import io
import json
from utils.creds_handler import CREDS
from config import DEFAULT_MAX_TOKENS


# Dictionary to cache clients based on api_key
CLIENTS = {}

API_KEY = CREDS.get("GOOGLE_API_KEY")
MODEL_NAME = CREDS.get("GOOGLE_MODEL_NAME")


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
            if isinstance(res, str):
                success7 = True
            else:
                success7 = False
                # Detailed diagnostics for unexpected response
                diagnostics = {
                    "type": str(type(response)),
                    "dir": str(dir(response)),
                }
                
                # Try to extract additional information from response object
                try:
                    if hasattr(response, "candidates"):
                        diagnostics["candidates_count"] = len(response.candidates)
                        diagnostics["candidates"] = [str(c) for c in response.candidates]
                    
                    if hasattr(response, "prompt_feedback"):
                        diagnostics["prompt_feedback"] = str(response.prompt_feedback)
                    
                    if hasattr(response, "usage_metadata"):
                        diagnostics["usage_metadata"] = str(response.usage_metadata)
                        
                    if hasattr(response, "finish_reason"):
                        diagnostics["finish_reason"] = str(response.finish_reason)
                        
                    if hasattr(response, "result"):
                        diagnostics["result"] = str(response.result)
                except Exception as diag_error:
                    diagnostics["diagnostic_error"] = str(diag_error)
                
                # Format diagnostics as pretty JSON
                formatted_diagnostics = json.dumps(diagnostics, indent=2)
                res = f"Google AI returned something strange of the type: {type(res)}\n\nDiagnostics:\n{formatted_diagnostics}"

        except errors.APIError as api_error:
            # Handle specific Google API errors with useful diagnostics
            error_info = {
                "error_type": "APIError",
                "code": getattr(api_error, "code", "unknown"),
                "message": str(api_error),
                "details": getattr(api_error, "details", None),
                "status": getattr(api_error, "status", None)
            }
            formatted_error = json.dumps(error_info, indent=2)
            res = f"Google AI API Error:\n{formatted_error}"
            print(res)
            success7 = False
            
        except Exception as e:
            # Capture the traceback in a string buffer
            traceback_buffer = io.StringIO()
            traceback.print_exc(file=traceback_buffer)
            traceback_str = traceback_buffer.getvalue()
            res = f"Google AI error: {e}\n\nTraceback:\n{traceback_str}"
            print(res)
            success7 = False

    return res, success7


def ask_google(messages, max_tokens=DEFAULT_MAX_TOKENS):
    model_name = CREDS.get("GOOGLE_MODEL_NAME")
    try:
        client = get_client()
        model_handle = client.get_model(f"models/{model_name}")

        response = get_response(
            messages, None, model_handle, api_key=API_KEY, mock7=False
        )
        
        return response.text, model_name

    except Exception as e:
        print(f"An error occurred in ask_google: {e}")
        return f"An error occurred in ask_google: {e}", model_name
