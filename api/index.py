from fastapi import FastAPI
import yt_dlp
import requests
import re

app = FastAPI()

# --- HELPER: VTT Cleaner (To make it look like a real transcript) ---
def clean_vtt_to_text(vtt_content: str):
    """
    VTT file ke kachre (timestamps, tags, headers) ko hatakar 
    saaf text return karta hai.
    """
    lines = vtt_content.splitlines()
    clean_lines = []
    seen_lines = set() # Duplicates hatane ke liye
    
    # Regex to match timestamps like "00:00:05.000 --> 00:00:07.000"
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}:\d{2}\.\d{3}')
    
    for line in lines:
        # Headers aur metadata ignore karo
        if line.startswith("WEBVTT") or line.strip() == "" or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        
        # Timestamp wali line ignore karo
        if timestamp_pattern.search(line):
            continue
            
        # Tags (<c>, <b> etc) hatao
        text = re.sub(r'<[^>]+>', '', line).strip()
        
        # Agar text khali nahi hai aur duplicate nahi hai to add karo
        # (Youtube ke vtt me aksar lines repeat hoti hain, isliye check zaruri hai)
        if text and text not in seen_lines:
            clean_lines.append(text)
            seen_lines.add(text)
            
    return " ".join(clean_lines)

# --- CORE LOGIC: YT-DLP EXTRACTOR ---
def get_yt_dlp_transcript(video_url):
    ydl_opts = {
        'skip_download': True,      # Video download mat karna
        'writesubtitles': True,     # Manual subs chahiye
        'writeautomaticsub': True,  # Auto-generated bhi chalega
        'subtitleslangs': ['en', 'hi'], # Pehle English, fir Hindi dhundo
        'quiet': True,              # Terminal me kachra mat dikhao
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Sirf Info extract karo (Network call)
            info = ydl.extract_info(video_url, download=False)
            
            # 2. Subtitles dhundo (Manual > Auto)
            subs = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})
            
            final_url = None
            
            # Priority 1: Manual English
            if 'en' in subs:
                final_url = subs['en'][0]['url'] # JSON3 ya VTT url
            # Priority 2: Manual Hindi
            elif 'hi' in subs:
                final_url = subs['hi'][0]['url']
            # Priority 3: Auto English
            elif 'en' in auto_subs:
                final_url = auto_subs['en'][0]['url']
            # Priority 4: Auto Hindi
            elif 'hi' in auto_subs:
                final_url = auto_subs['hi'][0]['url']
                
            # Agar abhi bhi nahi mila, to jo pehla available hai wo utha lo
            if not final_url:
                all_subs = {**subs, **auto_subs}
                if all_subs:
                    first_key = list(all_subs.keys())[0]
                    final_url = all_subs[first_key][0]['url']
            
            if final_url:
                # 3. URL mil gaya, ab content download karo (text format me)
                # Note: yt-dlp json3 format deta hai default me, par hum 'vtt' force kar sakte hain
                # lekin simple request se text uthana safe hai.
                response = requests.get(final_url)
                if response.status_code == 200:
                    # Agar JSON format hai to alag parsing, VTT hai to alag
                    # Zyadatar yt-dlp APIs json3 ya vtt return karte hain based on params.
                    # Hum raw text ko clean karenge.
                    return clean_vtt_to_text(response.text)
                    
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None

# --- API ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Online", "engine": "yt-dlp (Brahmastra)"}

@app.get("/api/transcript")
def get_transcript(url: str):
    if not url:
        return {"status": "error", "message": "URL to de bhai!"}

    # Asli yt-dlp logic
    transcript_text = get_yt_dlp_transcript(url)

    if transcript_text:
        separator = "\n" + "="*40 + "\n"
        final_output = (
            f"🎥 VIDEO TRANSCRIPT (Via Own Logic)\n"
            f"{separator}"
            f"{transcript_text}"
            f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ By @lakshitpatidar\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return {
            "status": "success", 
            "data": final_output
        }
    else:
        return {
            "status": "error", 
            "message": "❌ Transcript nahi mila. Shayad video private hai ya captions exist hi nahi karte."
        }
        
