import os
import json
import random
import re
import requests
import asyncio
import edge_tts
from moviepy.editor import *
from moviepy.config import change_settings

# --- CONFIG ---
change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})
BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
ASSETS_DIR = os.path.join(BASE_DIR, ".github/assets")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts/Montserrat-Bold.ttf")

if not os.path.exists(FONT_PATH): FONT_PATH = "DejaVu-Sans-Bold"
for d in [DATA_DIR, OUTPUT_DIR, CACHE_DIR]: os.makedirs(d, exist_ok=True)

# --- MODULE 1: FACT MINER (r/todayilearned) ---
class FactManager:
    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "weird_facts_history.json")
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try: return json.load(open(self.history_file))
            except: return []
        return []

    def save_history(self, entry_id):
        self.history.append(entry_id)
        with open(self.history_file, 'w') as f: json.dump(self.history, f)

    def clean_text(self, text):
        # Remove Reddit formatting like "TIL that", "TIL: ", etc.
        text = re.sub(r"(?i)^(til|today i learned)( that)?[:\s-]*", "", text)
        # Capitalize first letter
        return text[0].upper() + text[1:]

    def get_content(self):
        try:
            print("🧠 Mining r/todayilearned for weird facts...")
            headers = {'User-Agent': 'Mozilla/5.0'}
            url = "https://www.reddit.com/r/todayilearned/hot.json?limit=25"
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            
            for post in data['data']['children']:
                p = post['data']
                # Constraints: Short title (<200 chars) and Safe for Work
                if p['id'] not in self.history and not p['over_18'] and len(p['title']) < 200:
                    return {
                        "id": p['id'],
                        "text": self.clean_text(p['title'])
                    }
        except Exception as e:
            print(f"⚠️ Scrape failed: {e}")
        
        # Emergency Backup Facts
        backups = [
            ("b_01", "Wombat poop is cube-shaped to stop it from rolling away."),
            ("b_02", "Honey never spoils. You can eat 3000-year-old honey."),
            ("b_03", "Oxford University is older than the Aztec Empire."),
            ("b_04", "Nintendo was founded in 1889 and originally made playing cards.")
        ]
        sel = random.choice(backups)
        return {"id": sel[0], "text": sel[1]}

# --- MODULE 2: ASSET GENERATOR ---
class AssetGen:
    def get_fact_image(self, text):
        # Extract keywords for prompt (simple split)
        # We want a "Documentary" style look
        prompt = f"documentary photography, national geographic style, 4k, {text[:50]}"
        encoded = requests.utils.quote(prompt)
        url = f"https://pollinations.ai/p/{encoded}?width=1080&height=1920&nologo=true"
        filename = os.path.join(CACHE_DIR, f"fact_{hash(text)}.jpg")
        
        try:
            print(f"🎨 Generating Fact Image...")
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                return filename
        except: pass
        return None

# --- MODULE 3: RENDER ENGINE ---
async def generate_voice(text, filename):
    # Script wrapper to create suspense
    script = f"Here is a fact that sounds fake, but is actually true. {text}"
    communicate = edge_tts.Communicate(script, "en-US-EricNeural") # Energetic voice
    await communicate.save(filename)

def render_fact_video(data, audio_path, output_file):
    assets = AssetGen()
    
    # 1. Audio
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 1.5 # Slight pause at end
    
    # 2. Visuals (AI Image)
    img_path = assets.get_fact_image(data['text'])
    if img_path:
        clip = ImageClip(img_path).resize(height=1920).crop(x1=0, width=1080).set_duration(duration)
        # Darken for text readability
        darken = ColorClip(size=(1080, 1920), color=(0,0,0)).set_opacity(0.6).set_duration(duration)
        background = CompositeVideoClip([clip, darken])
    else:
        background = ColorClip(size=(1080, 1920), color=(20, 20, 30)).set_duration(duration)

    # 3. Header: "FAKE OR REAL?"
    header_box = ColorClip(size=(800, 150), color=(255, 200, 0)).set_position(('center', 150)).set_duration(duration)
    header_txt = TextClip("FAKE OR REAL?", font=FONT_PATH, fontsize=80, color='black').set_position(('center', 165)).set_duration(duration)

    # 4. The Fact Text
    # Wrap text logic (simple approx)
    fact_txt = TextClip(data['text'], font=FONT_PATH, fontsize=65, color='white', 
                        method='caption', size=(900, None), align='center', stroke_color='black', stroke_width=2)
    fact_txt = fact_txt.set_position('center').set_duration(duration)

    # 5. The "TRUE" Stamp (Appears at the end)
    # Trigger the stamp at 70% of the video
    stamp_time = duration * 0.7
    stamp_duration = duration - stamp_time
    
    stamp_box = ColorClip(size=(700, 200), color=(0, 200, 50)).set_position(('center', 1400)).set_start(stamp_time).set_duration(stamp_duration)
    stamp_txt = TextClip("✅ 100% TRUE", font=FONT_PATH, fontsize=90, color='white').set_position(('center', 1450)).set_start(stamp_time).set_duration(stamp_duration)

    # 6. Composite
    final = CompositeVideoClip([
        background, 
        header_box, header_txt,
        fact_txt,
        stamp_box, stamp_txt
    ]).set_audio(audio)
    
    final.write_videofile(output_file, fps=24, codec='libx264', audio_codec='aac', threads=4, preset='fast')

# --- MAIN ---
def main():
    mgr = FactManager()
    data = mgr.get_content()
    print(f"🧠 Fact: {data['text']}")
    
    audio_path = os.path.join(OUTPUT_DIR, "fact_voice.mp3")
    asyncio.run(generate_voice(data['text'], audio_path))
    
    vid_path = os.path.join(OUTPUT_DIR, f"weird_fact_{data['id']}.mp4")
    render_fact_video(data, audio_path, vid_path)
    
    mgr.save_history(data['id'])
    
    if os.path.exists(audio_path): os.remove(audio_path)
    for f in os.listdir(CACHE_DIR): os.remove(os.path.join(CACHE_DIR, f))

if __name__ == "__main__":
    main()