import os
import json
import random
import requests
import asyncio
import edge_tts
import numpy as np
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

# Ensure font fallback
if not os.path.exists(FONT_PATH): FONT_PATH = "DejaVu-Sans-Bold"

# --- MODULE 1: CONTENT (r/TwoSentenceHorror) ---
class HorrorContentManager:
    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "scary_history.json") # Separate history file
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try: return json.load(open(self.history_file))
            except: return []
        return []

    def save_history(self, entry_id):
        self.history.append(entry_id)
        with open(self.history_file, 'w') as f: json.dump(self.history, f)

    def get_content(self):
        try:
            print("👻 Scraping r/TwoSentenceHorror...")
            headers = {'User-Agent': 'Mozilla/5.0'}
            url = "https://www.reddit.com/r/TwoSentenceHorror/hot.json?limit=20"
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            
            for post in data['data']['children']:
                p = post['data']
                # Filter: Must be SFW-ish (no explicit tags) and not too long
                if p['id'] not in self.history and not p['over_18']:
                    return {
                        "id": p['id'],
                        "setup": p['title'],
                        "punchline": p['selftext']
                    }
        except Exception as e:
            print(f"⚠️ Scrape failed: {e}")
        
        # Backup Content
        return {
            "id": f"backup_{random.randint(1000,9999)}",
            "setup": "I heard my mom calling me into the kitchen.",
            "punchline": "As I ran down the hall, she whispered from the closet, 'Don't go, I heard it too.'"
        }

# --- MODULE 2: SCARY VISUALS ---
class HorrorAssetGen:
    def get_creepy_image(self, prompt):
        # Prompt engineering for horror
        horror_prompt = f"horror photography, grainy, vintage, dark atmosphere, scary, {prompt}"
        encoded = requests.utils.quote(horror_prompt)
        url = f"https://pollinations.ai/p/{encoded}?width=1080&height=1920&nologo=true"
        filename = os.path.join(CACHE_DIR, f"scary_{hash(prompt)}.jpg")
        
        try:
            print(f"🎨 Generating Horror Art: {prompt[:20]}...")
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                return filename
        except: pass
        return None

# --- MODULE 3: RENDER ENGINE ---
async def generate_scary_voice(text, filename):
    # Pitch -10Hz for creepiness, Rate -10% for suspense
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural", pitch="-15Hz", rate="-10%")
    await communicate.save(filename)

def render_scary_video(data, audio_path, output_file):
    assets = HorrorAssetGen()
    
    # 1. Audio
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 2.0
    
    # 2. Visuals (AI Image)
    # We use the "Setup" text to generate the image context
    img_path = assets.get_creepy_image(data['setup'])
    
    if img_path:
        # Slow Zoom Effect (Ken Burns)
        # MoviePy 1.x Zoom is hard, so we do a simple pan/crop or static with heavy vignette
        clip = ImageClip(img_path).resize(height=1920).crop(x1=0, width=1080).set_duration(duration)
    else:
        # Fallback: Black screen
        clip = ColorClip(size=(1080, 1920), color=(10, 0, 0)).set_duration(duration)

    # 3. Vignette (Darken Edges)
    # Create a radial gradient mask manually or just a dark overlay
    vignette = ColorClip(size=(1080, 1920), color=(0,0,0)).set_opacity(0.6).set_duration(duration)
    
    # 4. Text Logic (Display Setup... then Punchline)
    # Split text logic based on audio timing is hard without timestamps.
    # Strategy: Show Setup at Top, Punchline at Bottom appearing halfway.
    
    # Font Style
    txt_args = {"font": FONT_PATH, "color": "white", "method": "caption", "size": (900, None), "align": "center"}
    
    setup_txt = TextClip(f"\"{data['setup']}\"", fontsize=60, **txt_args)
    setup_txt = setup_txt.set_position(('center', 400)).set_duration(duration)
    
    # Punchline appears after 50% of video or hardcoded 3s delay if short
    punch_start = duration * 0.4
    punch_txt = TextClip(f"{data['punchline']}", fontsize=70, color="red", font=FONT_PATH, method="caption", size=(900, None), align="center")
    punch_txt = punch_txt.set_position(('center', 1100)).set_start(punch_start).set_duration(duration - punch_start)

    # 5. Composite
    final = CompositeVideoClip([clip, vignette, setup_txt, punch_txt]).set_audio(audio)
    final.write_videofile(output_file, fps=24, codec='libx264', audio_codec='aac', threads=4, preset='fast')

# --- MAIN ---
def main():
    mgr = HorrorContentManager()
    data = mgr.get_content()
    print(f"👻 Selected Story: {data['setup']}")
    
    # Generate Audio (Setup + Pause + Punchline)
    full_text = f"{data['setup']} ... ... {data['punchline']}"
    audio_path = os.path.join(OUTPUT_DIR, "scary_voice.mp3")
    asyncio.run(generate_scary_voice(full_text, audio_path))
    
    vid_path = os.path.join(OUTPUT_DIR, f"scary_{data['id']}.mp4")
    render_scary_video(data, audio_path, vid_path)
    
    mgr.save_history(data['id'])
    
    # Cleanup
    if os.path.exists(audio_path): os.remove(audio_path)
    for f in os.listdir(CACHE_DIR): os.remove(os.path.join(CACHE_DIR, f))

if __name__ == "__main__":
    main()