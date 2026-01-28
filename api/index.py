from fastapi import FastAPI
from youtube_transcript_api import YouTubeTranscriptApi
import re
from collections import Counter

app = FastAPI()

# --- HELPER FUNCTIONS ---

def extract_video_id(url):
    """URL se Video ID nikalne ka logic"""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def format_time(seconds):
    """Seconds ko [MM:SS] format me badalna"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"[{h:02d}:{m:02d}:{s:02d}]"
    return f"[{m:02d}:{s:02d}]"

def generate_smart_summary(text_list, num_sentences=10):
    """
    Summary Logic: Top keywords ke basis par important lines nikalna
    """
    full_text = " ".join([t['text'] for t in text_list])
    words = re.findall(r'\w+', full_text.lower())
    
    # Common words (stopwords) jo count nahi karne
    stopwords = set(['the', 'is', 'in', 'at', 'of', 'on', 'and', 'a', 'to', 'it', 'that', 'this', 'for', 'with', 'you', 'are', 'i', 'am', 'so', 'was', 'my'])
    
    # Word Frequency Count
    word_freq = Counter(w for w in words if w not in stopwords)
    max_freq = max(word_freq.values()) if word_freq else 1
    
    # Har sentence ko score dena
    ranked_sentences = []
    for item in text_list:
        sentence = item['text']
        score = 0
        for word in re.findall(r'\w+', sentence.lower()):
            if word in word_freq:
                score += word_freq[word]
        # Score normalize karna
        ranked_sentences.append((score / max_freq, sentence))
    
    # Top sentences pick karna (High score wale)
    ranked_sentences.sort(key=lambda x: x[0], reverse=True)
    top_sentences = [s[1] for s in ranked_sentences[:num_sentences]]
    
    return " ".join(top_sentences)

# --- MAIN API ---

@app.get("/")
def home():
    return {"status": "Online", "dev": "@lakshitpatidar"}

@app.get("/api/transcript")
def get_full_transcript(url: str):
    video_id = extract_video_id(url)
    if not video_id:
        return {"status": "error", "message": "Invalid URL provided."}

    try:
        # 1. Transcript Fetch Karna
        # 'list' wala error hatane ke liye direct call kar rahe hain
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en', 'en-IN'])
        
        # --- PART 1: WITH TIMESTAMPS ---
        timed_text = []
        for item in transcript:
            line = f"{format_time(item['start'])} {item['text']}"
            timed_text.append(line)
        full_timed_output = "\n".join(timed_text)

        # --- PART 2: PLAIN TEXT (WITHOUT TIMESTAMPS) ---
        plain_text_list = [item['text'] for item in transcript]
        full_plain_output = " ".join(plain_text_list)

        # --- PART 3: SMART SUMMARY ---
        # Agar video lambi hai (100+ lines) to top 15 lines, nahi to top 5
        summary_length = 15 if len(transcript) > 100 else 5
        smart_summary = generate_smart_summary(transcript, num_sentences=summary_length)

        # --- FINAL FORMATTING ---
        separator = "\n" + "="*40 + "\n"
        
        final_response = (
            f"🎥 VIDEO TRANSCRIPT & SUMMARY\n"
            f"🔗 ID: {video_id}\n"
            f"{separator}"
            f"📢 SECTION 1: TIMESTAMPS (Navigation)\n"
            f"{separator}"
            f"{full_timed_output}\n"
            f"{separator}"
            f"📄 SECTION 2: CLEAN READING (Text Only)\n"
            f"{separator}"
            f"{full_plain_output}\n"
            f"{separator}"
            f"🧠 SECTION 3: SMART SUMMARY (Auto-Generated)\n"
            f"{separator}"
            f"{smart_summary}..."
            f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Power by Lakshit API | 👨‍💻 Dev: @lakshitpatidar\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        return {
            "status": "success",
            "video_id": video_id,
            "data": final_response
        }

    except Exception as e:
        error_msg = str(e)
        if "Subtitles are disabled" in error_msg:
            return {"status": "error", "message": "⚠️ Is video ke subtitles disabled hain."}
        elif "No transcript found" in error_msg:
            return {"status": "error", "message": "⚠️ English/Hindi subtitles nahi mile."}
        else:
            return {"status": "error", "message": f"❌ Error: {error_msg}"}
                
