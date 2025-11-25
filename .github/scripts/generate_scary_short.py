import os
import json
import random
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

    
# --- CONFIG ---
change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})
BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
ASSETS_DIR = os.path.join(BASE_DIR, ".github/assets")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts/Montserrat-Bold.ttf")

if not os.path.exists(FONT_PATH): 
    FONT_PATH = "DejaVu-Sans-Bold"

for d in [DATA_DIR, OUTPUT_DIR, CACHE_DIR]: 
    os.makedirs(d, exist_ok=True)

# --- MODULE 1: CONTENT ---

class HorrorContentManager:
    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "scary_history.json")
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try: 
                return json.load(open(self.history_file))
            except: 
                return []
        return []

    def save_history(self, entry_id):
        self.history.append(entry_id)
        with open(self.history_file, 'w') as f: 
            json.dump(self.history, f)

    def get_content(self):
        try:
            print("👻 Scraping r/TwoSentenceHorror...")
            
            url = "https://api.pullpush.io/reddit/search/submission"
            params = {
                'subreddit': 'TwoSentenceHorror',
                'sort': 'desc',
                'sort_type': 'score',
                'size': 25,
                'fields': 'id,title,selftext,over_18'
            }
            
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                
                for post in data.get('data', []):
                    pid = post.get('id', '')
                    over_18 = post.get('over_18', False)
                    
                    if pid in self.history or over_18:
                        continue
                    
                    setup = post.get('title', '')
                    punchline = post.get('selftext', '')
                    
                    if setup and punchline:
                        print(f"✅ Found from Pushshift: {setup[:50]}...")
                        return {
                            "id": pid,
                            "setup": setup,
                            "punchline": punchline
                        }
        except Exception as e:
            print(f"⚠️ Scrape failed: {e}")
        
        backups = [
            ("I heard my mom calling me into the kitchen.", "As I ran down the hall, she whispered from the closet, 'Don't go, I heard it too.'"),
            ("I woke up to hear knocking on glass.", "At first, I thought it was the window until I heard it come from the mirror again."),
            ("The last man on Earth sat alone in a room.", "There was a knock on the door."),
            ("My daughter won't stop crying and screaming in the middle of the night.", "I visit her grave and ask her to stop, but it doesn't help."),
        ]
        
        setup, punchline = random.choice(backups)
        return {
            "id": f"backup_{random.randint(1000,9999)}",
            "setup": setup,
            "punchline": punchline
        }

# --- MODULE 2: SCARY VISUALS ---

class HorrorAssetGen:
    def get_creepy_image(self, prompt):
        filename = os.path.join(CACHE_DIR, f"scary_{abs(hash(prompt))}.jpg")
        width, height = 1080, 1920
        
        topic = "abstract"
        
        providers = [
            ("Pollinations", lambda: self._generate_pollinations(prompt, filename, width, height)),
            ("Unsplash", lambda: self._generate_unsplash(topic, filename, width, height)),
            ("Pexels", lambda: self._generate_pexels(topic, filename, width, height)),
            ("Picsum", lambda: self._generate_picsum(filename, width, height))
        ]
        
        for provider_name, provider_func in providers:
            try:
                print(f"🎨 Trying {provider_name} for horror image...")
                result = provider_func()
                if result and os.path.exists(result) and os.path.getsize(result) > 5000:
                    print(f"✅ {provider_name} succeeded")
                    return result
            except Exception as e:
                print(f"⚠️ {provider_name} failed: {str(e)[:50]}")
                continue
        
        print("⚠️ All providers failed, returning None for dark background")
        return None
    
    def _generate_pollinations(self, prompt, filename, width, height):
        horror_prompt = f"dark horror atmosphere, creepy, unsettling, grainy, vintage horror, {prompt}"
        negative = "bright,colorful,happy,cheerful,cartoon,text,logo,watermark"
        seed = random.randint(1, 999999)
        
        url = (
            f"https://image.pollinations.ai/prompt/{requests.utils.quote(horror_prompt)}"
            f"?width={width}&height={height}"
            f"&negative={requests.utils.quote(negative)}"
            f"&nologo=true&seed={seed}"
        )
        
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        raise Exception(f"Status {r.status_code}")
    
    def _generate_unsplash(self, topic, filename, width, height):
        seed = random.randint(1, 9999)
        url = f"https://source.unsplash.com/{width}x{height}/?dark,horror&sig={seed}"
        
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        raise Exception(f"Status {r.status_code}")
    
    def _generate_pexels(self, topic, filename, width, height):
        photo_ids = [3222684, 267614, 1402787, 8386440, 210186, 356056]
        photo_id = random.choice(photo_ids)
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
        url = f"https://picsum.photos/{width}/{height}?random={seed}&grayscale"
        
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        raise Exception(f"Status {r.status_code}")

# --- MODULE 3: AUDIO (FIXED KOKORO) ---

def generate_scary_voice(text, filename):
    """
    Generate creepy voice with pitch shifting
    """
    try:
        print("🎤 Generating scary voice with Kokoro...")
        import kokoro
        import numpy as np
        
        tts = kokoro.KPipeline(lang_code="en-us")
        audio_stream = tts(text, voice="am_adam", speed=0.95)
        
        audio_chunks = []
        for chunk in audio_stream:
            if isinstance(chunk, np.ndarray):
                audio_data = chunk
            elif hasattr(chunk, 'numpy'):
                audio_data = chunk.numpy()
            elif hasattr(chunk, '__array__'):
                audio_data = np.asarray(chunk)
            else:
                audio_data = np.array(chunk, dtype=np.float32)
            
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            audio_chunks.append(audio_data)
        
        if not audio_chunks:
            raise ValueError("No audio generated")
        
        audio_array = np.concatenate(audio_chunks, axis=0)
        
        max_val = np.abs(audio_array).max()
        if max_val > 1.0:
            audio_array = audio_array / max_val
        
        audio_int16 = (np.clip(audio_array, -1.0, 1.0) * 32767).astype(np.int16)
        
        import scipy.io.wavfile as wavfile
        temp_wav = filename.replace('.mp3', '_temp.wav')
        wavfile.write(temp_wav, 24000, audio_int16)
        
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_wav,
            '-af', 'asetrate=24000*0.92,atempo=1.087,aresample=24000,volume=1.2',
            '-codec:a', 'libmp3lame', '-qscale:a', '2',
            filename
        ], capture_output=True, timeout=30)
        
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        print(f"✅ Scary Kokoro voice generated")
        return True
        
    except Exception as e:
        print(f"⚠️ Kokoro failed: {str(e)[:100]}, using gTTS...")
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=True, tld='com')
        tts.save(filename)
        print(f"✅ gTTS fallback used")
        return True

# --- MODULE 4: RENDER ---

def render_scary_video(data, audio_path, output_file):
    assets = HorrorAssetGen()
    
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 2.0
    
    img_path = assets.get_creepy_image(data['setup'])
    
    if img_path:
        clip = ImageClip(img_path).resize(height=1920).crop(x1=0, width=1080).set_duration(duration)
    else:
        clip = ColorClip(size=(1080, 1920), color=(10, 0, 0)).set_duration(duration)

    vignette = ColorClip(size=(1080, 1920), color=(0,0,0)).set_opacity(0.6).set_duration(duration)
    
    txt_args = {"font": FONT_PATH, "color": "white", "method": "caption", "size": (900, None), "align": "center"}
    
    setup_txt = TextClip(f"\"{data['setup']}\"", fontsize=60, **txt_args)
    setup_txt = setup_txt.set_position(('center', 400)).set_duration(duration)
    
    punch_start = duration * 0.4
    punch_txt = TextClip(f"{data['punchline']}", fontsize=70, color="red", font=FONT_PATH, method="caption", size=(900, None), align="center")
    punch_txt = punch_txt.set_position(('center', 1100)).set_start(punch_start).set_duration(duration - punch_start)

    final = CompositeVideoClip([clip, vignette, setup_txt, punch_txt]).set_audio(audio)
    final.write_videofile(output_file, fps=24, codec='libx264', audio_codec='aac', threads=4, preset='fast')

# --- MAIN ---

def main():
    mgr = HorrorContentManager()
    data = mgr.get_content()
    print(f"👻 Selected Story: {data['setup']}")
    
    full_text = f"{data['setup']} ... ... {data['punchline']}"
    audio_path = os.path.join(OUTPUT_DIR, "scary_voice.mp3")
    generate_scary_voice(full_text, audio_path)
    
    vid_path = os.path.join(OUTPUT_DIR, f"scary_{data['id']}.mp4")
    render_scary_video(data, audio_path, vid_path)
    
    mgr.save_history(data['id'])
    
    if os.path.exists(audio_path): 
        os.remove(audio_path)
    for f in os.listdir(CACHE_DIR): 
        fp = os.path.join(CACHE_DIR, f)
        if os.path.isfile(fp): 
            os.remove(fp)

if __name__ == "__main__":
    main()