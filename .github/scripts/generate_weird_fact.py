import os
import json
import random
import re
import requests
import subprocess
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
        text = re.sub(r"(?i)^(til|today i learned)( that)?[:\s-]*", "", text)
        return text[0].upper() + text[1:] if text else text

    def get_content(self):
        try:
            print("🧠 Mining r/todayilearned for weird facts...")
            headers = {'User-Agent': 'Mozilla/5.0'}
            url = "https://www.reddit.com/r/todayilearned/hot.json?limit=25"
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            
            for post in data['data']['children']:
                p = post['data']
                if p['id'] not in self.history and not p['over_18'] and len(p['title']) < 200:
                    return {
                        "id": p['id'],
                        "text": self.clean_text(p['title'])
                    }
        except Exception as e:
            print(f"⚠️ Scrape failed: {e}")
        
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

# --- MODULE 3: AUDIO (Kokoro TTS) ---
def generate_voice(text, filename):
    """Generate energetic voice for facts"""
    try:
        print("🎤 Generating voice with Kokoro...")
        import kokoro
        
        script = f"Here is a fact that sounds fake, but is actually true. {text}"
        
        # Initialize pipeline
        pipeline = kokoro.KPipeline(lang_code="en-us")
        
        # Use energetic female voice
        audio_array = pipeline(script, voice="af_sarah")
        
        import scipy.io.wavfile as wav
        temp_wav = filename.replace('.mp3', '_temp.wav')
        wav.write(temp_wav, 24000, audio_array)
        
        subprocess.run([
            'ffmpeg', '-i', temp_wav,
            '-codec:a', 'libmp3lame', '-qscale:a', '2',
            '-y', filename
        ], check=True, capture_output=True, stderr=subprocess.PIPE)
        
        if os.path.exists(temp_wav): 
            os.remove(temp_wav)
            
    except Exception as e:
        print(f"⚠️ Kokoro failed ({e}), using gTTS...")
        from gtts import gTTS
        script = f"Here is a fact that sounds fake, but is actually true. {text}"
        tts = gTTS(text=script, lang='en', slow=False)
        tts.save(filename)

# --- MODULE 4: RENDER ENGINE ---
def render_fact_video(data, audio_path, output_file):
    assets = AssetGen()
    
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 1.5
    
    img_path = assets.get_fact_image(data['text'])
    if img_path:
        clip = ImageClip(img_path).resize(height=1920).crop(x1=0, width=1080).set_duration(duration)
        darken = ColorClip(size=(1080, 1920), color=(0,0,0)).set_opacity(0.6).set_duration(duration)
        background = CompositeVideoClip([clip, darken])
    else:
        background = ColorClip(size=(1080, 1920), color=(20, 20, 30)).set_duration(duration)

    header_box = ColorClip(size=(800, 150), color=(255, 200, 0)).set_position(('center', 150)).set_duration(duration)
    header_txt = TextClip("FAKE OR REAL?", font=FONT_PATH, fontsize=80, color='black').set_position(('center', 165)).set_duration(duration)

    fact_txt = TextClip(data['text'], font=FONT_PATH, fontsize=65, color='white', 
                        method='caption', size=(900, None), align='center', stroke_color='black', stroke_width=2)
    fact_txt = fact_txt.set_position('center').set_duration(duration)

    stamp_time = duration * 0.7
    stamp_duration = duration - stamp_time
    
    stamp_box = ColorClip(size=(700, 200), color=(0, 200, 50)).set_position(('center', 1400)).set_start(stamp_time).set_duration(stamp_duration)
    stamp_txt = TextClip("✅ 100% TRUE", font=FONT_PATH, fontsize=90, color='white').set_position(('center', 1450)).set_start(stamp_time).set_duration(stamp_duration)

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
    generate_voice(data['text'], audio_path)  # ← No asyncio
    
    vid_path = os.path.join(OUTPUT_DIR, f"weird_fact_{data['id']}.mp4")
    render_fact_video(data, audio_path, vid_path)
    
    mgr.save_history(data['id'])
    
    if os.path.exists(audio_path): os.remove(audio_path)
    for f in os.listdir(CACHE_DIR): 
        fp = os.path.join(CACHE_DIR, f)
        if os.path.isfile(fp): os.remove(fp)

if __name__ == "__main__":
    main()