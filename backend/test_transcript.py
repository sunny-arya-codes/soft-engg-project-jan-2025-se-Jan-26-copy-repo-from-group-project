#!/usr/bin/env python

from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(video_id):
    try:
        # Fetch the transcript without formatter
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Manual formatting
        transcript_text = ""
        for item in transcript_list:
            print(f"Item: {item}")
            
            # Make sure item is a dictionary and has the necessary keys
            if isinstance(item, dict) and all(key in item for key in ['text', 'start']):
                transcript_text += item.get('text', '') + ' '
        
        print(f"Successfully retrieved transcript for video {video_id}")
        if transcript_text:
            print(f"First 200 characters of transcript: {transcript_text[:200]}")
        
        return {
            "video_id": video_id,
            "transcription": transcript_text,
            "language": "en"
        }
        
    except Exception as e:
        print(f"Failed to get transcription for video {video_id}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "video_id": video_id,
            "transcription": None,
            "language": None
        }

if __name__ == "__main__":
    video_id = "hKm_rh1RTJQ"
    result = get_transcript(video_id)
    
    # Debug output
    print("\nResult dictionary keys:", result.keys())
    
    # Try to access transcription
    if "transcription" in result:
        print("Transcription exists:", bool(result["transcription"]))
        if result["transcription"]:
            print("Transcription length:", len(result["transcription"]))
    else:
        print("No transcription key in result")
        
    # Check for errors
    if "error" in result:
        print("Error:", result["error"])