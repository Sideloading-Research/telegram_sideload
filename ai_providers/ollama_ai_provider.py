
import os
from ollama import chat
from config import MAX_TOKENS_ALLOWED_IN_REQUEST

def ask_ollama(messages, max_tokens):
    model = os.environ.get("OLLAMA_MODEL", "gemma3")
    
    try:
        response = chat(
            model=model,
            messages=messages,
            options={
                'num_ctx': MAX_TOKENS_ALLOWED_IN_REQUEST,
                'num_predict': max_tokens
            }
        )
        
        content = response.get('message', {}).get('content', '')
        model_used = response.get('model', model)
        
        return content, model_used
        
    except Exception as e:
        print(f"An error occurred in ask_ollama: {e}")
        return f"Error in ask_ollama: {e}", model