import re
from youtube_transcript_api import YouTubeTranscriptApi

def get_youtube_video_id(url):
    """
    Extracts the video ID from a YouTube URL.
    """
    patron = r'(?:v=|\/)([0-9A-Za-z_-]{11})'
    resultado = re.search(patron, url)
    return resultado.group(1) if resultado else None

def extract_phrases_and_concatenate(json_data):
    """
    Extracts sentences from a JSON file and concatenates them into a single text variable.
    """
    sentence = []
    if isinstance(json_data, list):
        for item in json_data:
            if 'text' in item:
                sentence.append(item['text'])
    else:
        print("Unexpected JSON format")

    full_text = " ".join(sentence)
    return full_text

def get_transcript_from_url(url):
    """
    Tries to get the transcript for a YouTube URL.
    Returns the transcript text or None if failed.
    """
    video_id = get_youtube_video_id(url)
    if not video_id:
        return None
    
    try:
        # Try fetching transcript in Spanish first, then English, then auto-generated
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            transcript = transcript_list.find_manually_created_transcript(['es', 'en'])
        except:
            try:
                transcript = transcript_list.find_generated_transcript(['es', 'en'])
            except:
                transcript = next(iter(transcript_list))
        
        json_data = transcript.fetch()
        return extract_phrases_and_concatenate(json_data)
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def get_summarization_prompt(transcript_text):
    """
    Returns the prompt to be sent to the LLM for summarization.
    """
    return f"""STRICT INFORMATION PROCESSING INSTRUCTIONS:
1. OUTPUT FORMAT:
- Executive summary in maximum 5 points
- Neutral and direct language
- No subjective assessments
- Style: informative and objective

2. MANDATORY ANALYSIS:
- Identify MAIN FACTS
- Extract CONCRETE DATA
- Contextualize without personal opinion
- Prioritize verifiable information

3. RESTRICTIONS:
- Prohibited use of emotional adjectives
- Avoid personal interpretations
- Maximum linguistic neutrality
- Mathematical precision in description

4. STRUCTURE:
[Objective headline]
- Point 1: What happened
- Point 2: Who was involved
- Point 3: When and where
- Point 4: Immediate consequences
- Point 5: Relevant context

CONTENT TO SUMMARIZE:
{transcript_text}"""

def is_plugin_applicable(messages, provider):
    """
    Returns True if the last message from the user contains a YouTube link.
    The provider argument is used to check if the model supports native video processing.
    """
    if not messages:
        return False
    
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return False
    
    content = last_message.get("content", "")
    # Handle case where content might be a list (for images)
    if isinstance(content, list):
        # Check text parts
        for part in content:
            if part.get("type") == "text":
                text = part.get("text", "")
                if "youtube.com" in text or "youtu.be" in text:
                    return True
        return False
    
    if isinstance(content, str):
        if "youtube.com" in content or "youtu.be" in content:
            return True
            
    return False

def process_messages(messages, provider):
    """
    Modifies the messages by replacing the YouTube link with the transcript and summarization prompt.
    """
    if not messages:
        return messages

    last_message = messages[-1]
    content = last_message.get("content", "")
    
    url = None
    if isinstance(content, str):
        url = content
    elif isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                text = part.get("text", "")
                if "youtube.com" in text or "youtu.be" in text:
                    url = text
                    break
    
    if url:
        print(f"Plugin processing YouTube URL: {url}")
        transcript = get_transcript_from_url(url)
        if transcript:
            prompt = get_summarization_prompt(transcript)
            # Replace the content of the last message with the prompt
            # We keep the role as 'user' so the LLM thinks the user asked for this summary
            messages[-1]["content"] = prompt
            print("Plugin: Transcript attached to messages.")
        else:
            print("Plugin: Failed to fetch transcript.")
            
    return messages
