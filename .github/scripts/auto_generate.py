import os
import json
import random
import re
import requests
import subprocess
import numpy as np
from PIL import Image
from moviepy.editor import *
from moviepy.config import change_settings

# --- CONFIGURATION & SETUP ---

# Linux/GitHub Actions ImageMagick Path
change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

# Path Definitions
BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
ASSETS_DIR = os.path.join(BASE_DIR, ".github/assets")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts/Montserrat-Bold.ttf")

# Font Fallback to prevent crashes
if not os.path.exists(FONT_PATH):
    print("⚠️ Custom font not found. Using system default.")
    FONT_PATH = "DejaVu-Sans-Bold" # Ubuntu default

# Ensure Directories Exist
for d in [DATA_DIR, OUTPUT_DIR, CACHE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# --- MODULE 1: CONTENT ENGINE (Scraper + Backup) ---

class AutoContentManager:
    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "history.json")
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f: return json.load(f)
            except: return []
        return []

    def save_history(self, entry_id):
        self.history.append(entry_id)
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def get_content(self):
        # 1. Try Reddit Scrape
        try:
            print("🌐 Scraping r/WouldYouRather...")
            content = self._scrape_reddit()
            if content and content['id'] not in self.history:
                return content
        except Exception as e:
            print(f"⚠️ Scrape Error: {e}")

        # 2. Fallback Generator
        print("🛡️ Engaging Offline Backup Generator...")
        return self._generate_offline()

    def _scrape_reddit(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = "https://www.reddit.com/r/WouldYouRather/hot.json?limit=15"
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        
        for post in data['data']['children']:
            title = post['data']['title']
            pid = post['data']['id']
            
            # Regex to extract A and B
            match = re.search(r"(?i)would you rather\s+(.*?)\s+(?:or|,\s*or)\s+(.*)", title)
            if match:
                opt_a = match.group(1).strip('?.! ')
                opt_b = match.group(2).strip('?.! ')
                
                # Simulate stats based on upvote ratio
                ratio = post['data']['upvote_ratio']
                stat_a = int(ratio * 100)
                
                # Add variance so it's not always clean numbers
                if stat_a > 90: stat_a = 88
                if stat_a < 10: stat_a = 12
                
                return {
                    "id": pid,
                    "option_a": opt_a,
                    "option_b": opt_b,
                    "stats": [stat_a, 100-stat_a]
                }
        return None

    def _generate_offline(self):
        # Content Bank
        verbs = ["Eat", "Fight", "Marry", "Lose", "Live with", "Be trapped with"]
        nouns = ["a T-Rex", "Elon Musk", "a Crying Baby", "your Ex", "a Ghost", "1000 Rats"]
        conditions = ["forever", "in space", "underwater", "every Tuesday", "naked"]
        
        opt_a = f"{random.choice(verbs)} {random.choice(nouns)} {random.choice(conditions)}"
        opt_b = f"{random.choice(verbs)} {random.choice(nouns)} {random.choice(conditions)}"
        
        pid = str(hash(opt_a + opt_b))
        s1 = random.randint(35, 65)
        
        return {"id": pid, "option_a": opt_a, "option_b": opt_b, "stats": [s1, 100-s1]}

# --- MODULE 2: VISUAL ASSETS (Pollinations AI + Gradients) ---

class AssetGenerator:
    def get_ai_image(self, prompt, side):
        """Fetches image from Pollinations.ai"""
        clean_prompt = f"cinematic lighting, hyperrealistic, 4k, detailed, {prompt}"
        encoded = requests.utils.quote(clean_prompt)
        url = f"https://pollinations.ai/p/{encoded}?width=1080&height=960&nologo=true"
        filename = os.path.join(CACHE_DIR, f"{side}_{hash(prompt)}.jpg")
        
        try:
            print(f"🎨 Generating AI Art: {prompt[:30]}...")
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(r.content)
                return filename
        except:
            print("⚠️ Image Gen failed, using fallback.")
        return None

    def create_gradient(self, w, h, c1, c2):
        """NumPy Gradient Generator"""
        r1, g1, b1 = c1
        r2, g2, b2 = c2
        base = np.linspace(0, 1, h)
        r = np.tile(np.linspace(r1, r2, h).reshape(h, 1), (1, w))
        g = np.tile(np.linspace(g1, g2, h).reshape(h, 1), (1, w))
        b = np.tile(np.linspace(b1, b2, h).reshape(h, 1), (1, w))
        gradient = np.dstack((r, g, b)).astype(np.uint8)
        return ImageClip(gradient)

# --- MODULE 3: VIDEO COMPOSITOR ---

def render_video(scenario, audio_path, output_file):
    print(f"🎬 Rendering: {scenario['option_a']} vs {scenario['option_b']}")
    assets = AssetGenerator()
    
    # Audio Setup
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration + 5.0 # 3s think + 2s reveal
    W, H = 1080, 1920

    # 1. Background Layer (AI Image OR Gradient)
    def get_bg(text, side, fallback_colors, pos):
        img_path = assets.get_ai_image(text, side)
        if img_path and os.path.exists(img_path):
            clip = ImageClip(img_path).resize(newsize=(W, H//2))
            # Dark Overlay for text readability
            darken = ColorClip(size=(W, H//2), color=(0,0,0)).set_opacity(0.55)
            return CompositeVideoClip([clip, darken]).set_position(pos).set_duration(duration)
        else:
            return assets.create_gradient(W, H//2, fallback_colors[0], fallback_colors[1])\
                   .set_position(pos).set_duration(duration)

    bg_top = get_bg(scenario['option_a'], "top", [(200, 40, 40), (100, 20, 20)], ('center', 'top'))
    bg_btm = get_bg(scenario['option_b'], "btm", [(40, 80, 200), (20, 40, 100)], ('center', 'bottom'))

    # 2. Text Helpers (Shadow + Main)
    def make_text(txt, size, pos, start=0):
        # Shadow
        s = TextClip(txt, font=FONT_PATH, fontsize=size, color='black', 
                     method='caption', size=(900, None), align='center')
        s = s.set_position((pos[0]+4, pos[1]+4)).set_opacity(0.6).set_start(start).set_duration(duration-start)
        # Main
        m = TextClip(txt, font=FONT_PATH, fontsize=size, color='white', 
                     method='caption', size=(900, None), align='center')
        m = m.set_position(pos).set_start(start).set_duration(duration-start)
        return s, m

    # 3. UI Elements
    head_s, head_m = make_text("WOULD YOU RATHER?", 80, ('center', 130))
    opt_a_s, opt_a_m = make_text(scenario['option_a'], 70, ('center', 450))
    opt_b_s, opt_b_m = make_text(scenario['option_b'], 70, ('center', 1400))

    # VS Badge
    vs_box = ColorClip(size=(220, 160), color=(20,20,20)).set_position('center').set_duration(duration)
    vs_txt = TextClip("VS", font=FONT_PATH, fontsize=85, color='white').set_position('center').set_duration(duration)

    # 4. Countdown Timer (Yellow Bar)
    timer_y = H // 2 + 80
    timer_bg = ColorClip(size=(W, 20), color=(50,50,50)).set_position(('center', timer_y)).set_duration(duration)
    
    choice_time = duration - 2.0
    # Dynamic width lambda
    def width_maker(t):
        if t > choice_time: return 0
        return int(W * (1 - (t / choice_time)))
    
    # Use a moving clip to simulate shrinking because resizing is buggy in MoviePy 1.0.3
    timer_fill = ColorClip(size=(W, 20), color=(255, 200, 0))
    timer_fill = timer_fill.set_position(lambda t: (-int(W * (t/choice_time)), timer_y) if t < choice_time else (-W, timer_y))
    timer_fill = timer_fill.set_duration(duration)

    # 5. Stats Reveal
    reveal_start = duration - 2.0
    stat_a_s, stat_a_m = make_text(f"{scenario['stats'][0]}%", 140, ('center', 700), start=reveal_start)
    stat_b_s, stat_b_m = make_text(f"{scenario['stats'][1]}%", 140, ('center', 1650), start=reveal_start)

    # 6. Final Composite
    final = CompositeVideoClip([
        bg_top, bg_btm,
        head_s, head_m,
        vs_box, vs_txt,
        opt_a_s, opt_a_m,
        opt_b_s, opt_b_m,
        timer_bg, timer_fill,
        stat_a_s, stat_a_m,
        stat_b_s, stat_b_m
    ])
    
    final = final.set_audio(audio_clip)
    final.write_videofile(output_file, fps=24, codec='libx264', audio_codec='aac', threads=4, preset='fast')

# --- MODULE 4: AUDIO GENERATION (Kokoro TTS) ---

def generate_audio(text, filename):
    """
    Generate natural-sounding audio using Kokoro TTS
    Fallback to gTTS if Kokoro fails
    """
    try:
        print("🎤 Generating audio with Kokoro TTS...")
        import kokoro
        
        # Initialize voice (choose one below)
        voice = kokoro.KPipeline(
            lang_code="en-us", 
            voice="af_bella"  # Options: af_bella, af_sarah, am_adam, am_michael, bf_emma
        )
        
        # Generate audio array
        audio_array = voice(text)
        
        # Save as WAV first
        temp_wav = filename.replace('.mp3', '_temp.wav')
        
        # Write WAV file
        import scipy.io.wavfile as wav
        wav.write(temp_wav, 24000, audio_array)
        
        # Convert to MP3 using ffmpeg
        subprocess.run([
            'ffmpeg', '-i', temp_wav, 
            '-codec:a', 'libmp3lame', 
            '-qscale:a', '2',  # High quality
            '-y', filename
        ], check=True, capture_output=True, stderr=subprocess.PIPE)
        
        # Cleanup temp file
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        print(f"✅ Audio saved: {filename}")
        
    except Exception as e:
        print(f"⚠️ Kokoro TTS failed ({e}), using gTTS fallback...")
        
        # Fallback to gTTS
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en', slow=False, tld='com')
            tts.save(filename)
            print(f"✅ Audio saved with gTTS: {filename}")
        except Exception as gtts_error:
            print(f"❌ Both TTS methods failed: {gtts_error}")
            # Create silent audio as last resort
            silent = AudioClip(lambda t: 0, duration=5)
            silent.write_audiofile(filename, fps=44100, codec='libmp3lame')

# --- EXECUTION ---

def main():
    # 1. Get Content
    mgr = AutoContentManager()
    data = mgr.get_content()
    
    print(f"✅ LOCKED: {data['option_a']} vs {data['option_b']}")
    
    # 2. Generate Audio (NOW SYNCHRONOUS - NO ASYNCIO)
    audio_script = f"Would you rather {data['option_a']}, or {data['option_b']}? Make your choice."
    audio_path = os.path.join(OUTPUT_DIR, "voice.mp3")
    generate_audio(audio_script, audio_path)
    
    # 3. Render Video
    video_path = os.path.join(OUTPUT_DIR, f"wyr_{data['id']}.mp4")
    render_video(data, audio_path, video_path)
    
    # 4. Update History
    mgr.save_history(data['id'])
    
    # 5. Cleanup
    if os.path.exists(audio_path): 
        os.remove(audio_path)
    # Clean cache to prevent disk bloat
    for f in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    print("✨ DONE. Video ready in output/")

if __name__ == "__main__":
    main()