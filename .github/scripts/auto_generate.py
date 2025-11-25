import os
import json
import random
import re
import requests
import subprocess
import time
import numpy as np
from PIL import Image
from moviepy.editor import *
from moviepy.config import change_settings

# Add this right after your imports, before any other code:

# Fix PIL.Image.ANTIALIAS deprecation for MoviePy compatibility
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
if not hasattr(Image, 'BILINEAR'):
    Image.BILINEAR = Image.LANCZOS

# --- CONFIGURATION & SETUP ---

change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})

BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
ASSETS_DIR = os.path.join(BASE_DIR, ".github/assets")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts/Montserrat-Bold.ttf")

if not os.path.exists(FONT_PATH):
    print("⚠️ Custom font not found. Using system default.")
    FONT_PATH = "DejaVu-Sans-Bold"

for d in [DATA_DIR, OUTPUT_DIR, CACHE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# --- MODULE 1: CONTENT ENGINE ---

class AutoContentManager:
    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "history.json")
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f: 
                    return json.load(f)
            except: 
                return []
        return []

    def save_history(self, entry_id):
        self.history.append(entry_id)
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def get_content(self):
        try:
            print("🌐 Scraping r/WouldYouRather...")
            content = self._scrape_reddit()
            if content and content['id'] not in self.history:
                return content
        except Exception as e:
            print(f"⚠️ Scrape Error: {e}")

        print("🛡️ Engaging Offline Backup Generator...")
        return self._generate_offline()

    def _scrape_reddit(self):
        try:
            print("🌐 Fetching from Pushshift archive...")
            url = "https://api.pullpush.io/reddit/search/submission"
            params = {
                'subreddit': 'WouldYouRather',
                'sort': 'desc',
                'sort_type': 'score',
                'size': 25,
                'fields': 'id,title,score'
            }
            
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                
                for post in data.get('data', []):
                    title = post.get('title', '')
                    pid = post.get('id', '')
                    
                    if pid in self.history:
                        continue
                    
                    match = re.search(r"(?i)would you rather\s+(.*?)\s+(?:or|,\s*or)\s+(.*)", title)
                    if match:
                        opt_a = match.group(1).strip('?.! ')
                        opt_b = match.group(2).strip('?.! ')
                        
                        score = post.get('score', 100)
                        stat_a = min(max(int((score % 60) + 20), 25), 75)
                        
                        print(f"✅ Found from Pushshift: {title[:50]}...")
                        return {
                            "id": pid,
                            "option_a": opt_a,
                            "option_b": opt_b,
                            "stats": [stat_a, 100-stat_a]
                        }
        except Exception as e:
            print(f"⚠️ Pushshift failed: {e}")
        
        return None

    def _generate_offline(self):
        verbs = ["Eat", "Fight", "Marry", "Lose", "Live with", "Be trapped with"]
        nouns = ["a T-Rex", "Elon Musk", "a Crying Baby", "your Ex", "a Ghost", "1000 Rats"]
        conditions = ["forever", "in space", "underwater", "every Tuesday", "naked"]
        
        opt_a = f"{random.choice(verbs)} {random.choice(nouns)} {random.choice(conditions)}"
        opt_b = f"{random.choice(verbs)} {random.choice(nouns)} {random.choice(conditions)}"
        
        pid = str(abs(hash(opt_a + opt_b)))
        s1 = random.randint(35, 65)
        
        return {"id": pid, "option_a": opt_a, "option_b": opt_b, "stats": [s1, 100-s1]}

# --- MODULE 2: VISUAL ASSETS ---

class AssetGenerator:
    def get_ai_image(self, prompt, side):
        """Multi-provider image generation with smart fallbacks"""
        filename = os.path.join(CACHE_DIR, f"{side}_{abs(hash(prompt))}.jpg")
        width, height = 1080, 960
        
        topic_keywords = prompt.lower()
        if "fight" in topic_keywords or "battle" in topic_keywords:
            topic = "action"
        elif "eat" in topic_keywords or "food" in topic_keywords:
            topic = "food"
        elif "space" in topic_keywords or "universe" in topic_keywords:
            topic = "space"
        elif "underwater" in topic_keywords or "ocean" in topic_keywords or "water" in topic_keywords:
            topic = "nature"
        elif "ghost" in topic_keywords or "scary" in topic_keywords:
            topic = "abstract"
        else:
            topic = "people"
        
        providers = [
            ("Pollinations", lambda: self._generate_pollinations(prompt, filename, width, height)),
            ("Unsplash", lambda: self._generate_unsplash(topic, filename, width, height)),
            ("Pexels", lambda: self._generate_pexels(topic, filename, width, height)),
            ("Picsum", lambda: self._generate_picsum(filename, width, height))
        ]
        
        for provider_name, provider_func in providers:
            try:
                print(f"🎨 Trying {provider_name}: {prompt[:30]}...")
                result = provider_func()
                if result and os.path.exists(result) and os.path.getsize(result) > 5000:
                    print(f"✅ {provider_name} succeeded")
                    return result
            except Exception as e:
                print(f"⚠️ {provider_name} failed: {str(e)[:50]}")
                continue
        
        print("⚠️ All providers failed, using gradient")
        return None
    
    def _generate_pollinations(self, prompt, filename, width, height):
        negative = "blurry,low quality,watermark,text,logo,ui,overlay,frame,border"
        formatted = f"{prompt}, cinematic, detailed, vibrant, no text, no logos, clean image"
        seed = random.randint(1, 999999)
        
        url = (
            f"https://image.pollinations.ai/prompt/{requests.utils.quote(formatted)}"
            f"?width={width}&height={height}"
            f"&negative={requests.utils.quote(negative)}"
            f"&nologo=true&enhance=true&seed={seed}"
        )
        
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        raise Exception(f"Status {r.status_code}")
    
    def _generate_unsplash(self, topic, filename, width, height):
        seed = random.randint(1, 9999)
        url = f"https://source.unsplash.com/{width}x{height}/?{topic}&sig={seed}"
        
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        raise Exception(f"Status {r.status_code}")
    
    def _generate_pexels(self, topic, filename, width, height):
        photo_ids = {
            "action": [2045531, 6153896, 8386440, 1181244, 4974912, 3861959],
            "food": [1640777, 1410235, 2097090, 262959, 3338496, 3764640],
            "space": [2387873, 59989, 132037, 145035, 210186, 62415],
            "nature": [34950, 3222684, 2014422, 590041, 15286, 36717],
            "people": [3184395, 3184325, 1671643, 1181671, 1222271, 1546906],
            "abstract": [3222684, 267614, 1402787, 8386440, 210186, 356056]
        }
        
        ids = photo_ids.get(topic, photo_ids["abstract"])
        photo_id = random.choice(ids)
        seed = random.randint(1000, 9999)
        
        url = f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w={width}&h={height}&random={seed}"
        
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            
            img = Image.open(filename).convert("RGB")
            img = img.resize((width, height), Image.LANCZOS)
            img.save(filename, quality=95)
            return filename
        raise Exception(f"Status {r.status_code}")
    
    def _generate_picsum(self, filename, width, height):
        seed = random.randint(1, 1000)
        url = f"https://picsum.photos/{width}/{height}?random={seed}"
        
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        raise Exception(f"Status {r.status_code}")

    def create_gradient(self, w, h, c1, c2):
        r1, g1, b1 = c1
        r2, g2, b2 = c2
        r = np.tile(np.linspace(r1, r2, h).reshape(h, 1), (1, w))
        g = np.tile(np.linspace(g1, g2, h).reshape(h, 1), (1, w))
        b = np.tile(np.linspace(b1, b2, h).reshape(h, 1), (1, w))
        gradient = np.dstack((r, g, b)).astype(np.uint8)
        return ImageClip(gradient)

# --- MODULE 3: VIDEO COMPOSITOR ---

def render_video(scenario, audio_path, output_file):
    print(f"🎬 Rendering: {scenario['option_a']} vs {scenario['option_b']}")
    assets = AssetGenerator()
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration + 5.0
    W, H = 1080, 1920

    def get_bg(text, side, fallback_colors, pos):
        img_path = assets.get_ai_image(text, side)
        if img_path and os.path.exists(img_path):
            clip = ImageClip(img_path).resize(newsize=(W, H//2))
            darken = ColorClip(size=(W, H//2), color=(0,0,0)).set_opacity(0.55)
            return CompositeVideoClip([clip, darken]).set_position(pos).set_duration(duration)
        else:
            return assets.create_gradient(W, H//2, fallback_colors[0], fallback_colors[1])\
                   .set_position(pos).set_duration(duration)

    bg_top = get_bg(scenario['option_a'], "top", [(200, 40, 40), (100, 20, 20)], ('center', 'top'))
    bg_btm = get_bg(scenario['option_b'], "btm", [(40, 80, 200), (20, 40, 100)], ('center', 'bottom'))

    def make_text(txt, size, pos, start=0):
        s = TextClip(txt, font=FONT_PATH, fontsize=size, color='black', 
                     method='caption', size=(900, None), align='center')
        
        if isinstance(pos[0], str) and pos[0] == 'center':
            shadow_pos = ('center', pos[1] + 4)
        else:
            shadow_pos = (pos[0] + 4, pos[1] + 4)
        
        s = s.set_position(shadow_pos).set_opacity(0.6).set_start(start).set_duration(duration-start)
        
        m = TextClip(txt, font=FONT_PATH, fontsize=size, color='white', 
                     method='caption', size=(900, None), align='center')
        m = m.set_position(pos).set_start(start).set_duration(duration-start)
        return s, m

    head_s, head_m = make_text("WOULD YOU RATHER?", 80, ('center', 130))
    opt_a_s, opt_a_m = make_text(scenario['option_a'], 70, ('center', 450))
    opt_b_s, opt_b_m = make_text(scenario['option_b'], 70, ('center', 1400))

    vs_box = ColorClip(size=(220, 160), color=(20,20,20)).set_position('center').set_duration(duration)
    vs_txt = TextClip("VS", font=FONT_PATH, fontsize=85, color='white').set_position('center').set_duration(duration)

    timer_y = H // 2 + 80
    timer_bg = ColorClip(size=(W, 20), color=(50,50,50)).set_position(('center', timer_y)).set_duration(duration)
    
    choice_time = duration - 2.0
    timer_fill = ColorClip(size=(W, 20), color=(255, 200, 0))
    timer_fill = timer_fill.set_position(
        lambda t: (-int(W * (t/choice_time)), timer_y) if t < choice_time else (-W, timer_y)
    ).set_duration(duration)

    reveal_start = duration - 2.0
    stat_a_s, stat_a_m = make_text(f"{scenario['stats'][0]}%", 140, ('center', 700), start=reveal_start)
    stat_b_s, stat_b_m = make_text(f"{scenario['stats'][1]}%", 140, ('center', 1650), start=reveal_start)

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

# --- MODULE 4: AUDIO GENERATION (FIXED KOKORO) ---
def generate_audio(text, filename):
    """Generate audio with Kokoro - handle nested sequences."""
    try:
        import kokoro
        import numpy as np
        import torch
        from scipy.io import wavfile
        import subprocess
        import os
        
        print("🎤 Generating audio with Kokoro TTS...")
        
        pipeline = kokoro.KPipeline(lang_code="en-us", repo_id='hexgrad/Kokoro-82M')
        result = pipeline(text, voice="af_bella")
        
        # Convert generator to list immediately
        chunks_list = list(result)
        
        # NUCLEAR OPTION: Recursively extract all float values
        all_values = []
        
        def extract_floats(obj):
            """Extract all float values from nested structure."""
            if isinstance(obj, torch.Tensor):
                all_values.extend(obj.detach().cpu().numpy().flatten().tolist())
            elif isinstance(obj, np.ndarray):
                all_values.extend(obj.flatten().tolist())
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    extract_floats(item)
            elif isinstance(obj, (int, float)):
                all_values.append(float(obj))
        
        # Extract from all chunks
        for chunk in chunks_list:
            extract_floats(chunk)
        
        if len(all_values) == 0:
            raise ValueError("No audio samples extracted")
        
        print(f"  ✓ Extracted {len(all_values)} audio samples")
        
        # Convert to numpy array
        audio_array = np.array(all_values, dtype=np.float32)
        
        # Normalize
        max_val = np.abs(audio_array).max()
        if max_val > 0:
            audio_array = audio_array / max_val
        audio_array = np.clip(audio_array, -1.0, 1.0)
        
        # Convert to 16-bit
        audio_int16 = (audio_array * 32767).astype(np.int16)
        
        # Save WAV
        wav_temp = filename.replace('.mp3', '_kokoro.wav')
        wavfile.write(wav_temp, 24000, audio_int16)
        
        # Convert to MP3
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error',
            '-i', wav_temp, '-codec:a', 'libmp3lame',
            '-qscale:a', '2', filename
        ], check=True, capture_output=True)
        
        os.remove(wav_temp)
        
        print(f"✅ Kokoro audio saved: {filename}")
        return filename
        
    except Exception as e:
        print(f"⚠️ Kokoro failed: {str(e)[:100]}")
        print("    🔄 Using gTTS...")
        
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        print(f"✅ gTTS audio saved: {filename}")
        return filename
            
# --- EXECUTION ---

def main():
    mgr = AutoContentManager()
    data = mgr.get_content()
    
    print(f"✅ LOCKED: {data['option_a']} vs {data['option_b']}")
    
    audio_script = f"Would you rather {data['option_a']}, or {data['option_b']}? Make your choice."
    audio_path = os.path.join(OUTPUT_DIR, "voice.mp3")
    generate_audio(audio_script, audio_path)
    
    video_path = os.path.join(OUTPUT_DIR, f"wyr_{data['id']}.mp4")
    render_video(data, audio_path, video_path)
    
    mgr.save_history(data['id'])
    
    if os.path.exists(audio_path): 
        os.remove(audio_path)
    
    for f in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    print("✨ DONE. Video ready in output/")

if __name__ == "__main__":
    main()