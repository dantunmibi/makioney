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

# --- MODULE 1: FACT MINER ---

class FactManager:
    def __init__(self):
        self.history_file = os.path.join(DATA_DIR, "weird_facts_history.json")
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

    def clean_text(self, text):
        text = re.sub(r"(?i)^(til|today i learned)( that)?[:\s-]*", "", text)
        return text[0].upper() + text[1:] if text else text

    def get_content(self):
        try:
            print("🧠 Mining r/todayilearned for weird facts...")
            
            url = "https://api.pullpush.io/reddit/search/submission"
            params = {
                'subreddit': 'todayilearned',
                'sort': 'desc',
                'sort_type': 'score',
                'size': 30,
                'fields': 'id,title,over_18'
            }
            
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                
                for post in data.get('data', []):
                    pid = post.get('id', '')
                    title = post.get('title', '')
                    over_18 = post.get('over_18', False)
                    
                    if pid in self.history or over_18 or len(title) > 200:
                        continue
                    
                    cleaned = self.clean_text(title)
                    if cleaned:
                        print(f"✅ Found from Pushshift: {cleaned[:50]}...")
                        return {
                            "id": pid,
                            "text": cleaned
                        }
        except Exception as e:
            print(f"⚠️ Scrape failed: {e}")
        
        backups = [
            ("b_01", "Wombat poop is cube-shaped to stop it from rolling away."),
            ("b_02", "Honey never spoils. You can eat 3000-year-old honey."),
            ("b_03", "Oxford University is older than the Aztec Empire."),
            ("b_04", "Nintendo was founded in 1889 and originally made playing cards."),
            ("b_05", "A group of flamingos is called a 'flamboyance'."),
            ("b_06", "Octopuses have three hearts and blue blood."),
            ("b_07", "Bananas are berries, but strawberries aren't."),
            ("b_08", "There are more possible iterations of a chess game than atoms in the known universe."),
        ]
        sel = random.choice(backups)
        return {"id": sel[0], "text": sel[1]}

# --- MODULE 2: ASSET GENERATOR ---

class AssetGen:
    def get_fact_image(self, text):
        filename = os.path.join(CACHE_DIR, f"fact_{abs(hash(text))}.jpg")
        width, height = 1080, 1920
        
        text_lower = text.lower()
        if any(word in text_lower for word in ["animal", "wombat", "octopus", "flamingo"]):
            topic = "nature"
        elif any(word in text_lower for word in ["food", "honey", "banana"]):
            topic = "food"
        elif any(word in text_lower for word in ["university", "history", "oxford", "aztec"]):
            topic = "abstract"
        elif any(word in text_lower for word in ["nintendo", "chess", "game"]):
            topic = "technology"
        else:
            topic = "abstract"
        
        providers = [
            ("Pollinations", lambda: self._generate_pollinations(text, filename, width, height)),
            ("Unsplash", lambda: self._generate_unsplash(topic, filename, width, height)),
            ("Pexels", lambda: self._generate_pexels(topic, filename, width, height)),
            ("Picsum", lambda: self._generate_picsum(filename, width, height))
        ]
        
        for provider_name, provider_func in providers:
            try:
                print(f"🎨 Trying {provider_name} for fact image...")
                result = provider_func()
                if result and os.path.exists(result) and os.path.getsize(result) > 5000:
                    print(f"✅ {provider_name} succeeded")
                    return result
            except Exception as e:
                print(f"⚠️ {provider_name} failed: {str(e)[:50]}")
                continue
        
        print("⚠️ All providers failed, returning None for colored background")
        return None
    
    def _generate_pollinations(self, text, filename, width, height):
        prompt = f"educational illustration, documentary style, professional, {text[:50]}"
        negative = "text,logo,watermark,ui,overlay"
        seed = random.randint(1, 999999)
        
        url = (
            f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
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
        url = f"https://source.unsplash.com/{width}x{height}/?{topic},education&sig={seed}"
        
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            with open(filename, 'wb') as f:
                f.write(r.content)
            return filename
        raise Exception(f"Status {r.status_code}")
    
    def _generate_pexels(self, topic, filename, width, height):
        photo_ids = {
            "nature": [34950, 3222684, 2014422, 590041, 15286, 36717],
            "food": [1640777, 1410235, 2097090, 262959, 3338496, 3764640],
            "technology": [2045531, 6153896, 8386440, 1181244, 4974912, 3861959],
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

# --- MODULE 3: AUDIO (FIXED KOKORO) ---

def generate_voice(text, filename):
    """
    Generate energetic voice for facts
    """
    try:
        print("🎤 Generating voice with Kokoro...")
        import kokoro
        import numpy as np
        
        script = f"Here is a fact that sounds fake, but is actually true. {text}"
        
        tts = kokoro.KPipeline(lang_code="en-us")
        audio_stream = tts(script, voice="af_sarah", speed=1.05)
        
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
            '-codec:a', 'libmp3lame', '-qscale:a', '2',
            '-ar', '24000',
            filename
        ], capture_output=True, timeout=30)
        
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        print(f"✅ Kokoro voice generated")
        return True
        
    except Exception as e:
        print(f"⚠️ Kokoro failed: {str(e)[:100]}, using gTTS...")
        from gtts import gTTS
        script = f"Here is a fact that sounds fake, but is actually true. {text}"
        tts = gTTS(text=script, lang='en', slow=False, tld='com')
        tts.save(filename)
        print(f"✅ gTTS fallback used")
        return True

# --- MODULE 4: RENDER ---

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
    generate_voice(data['text'], audio_path)
    
    vid_path = os.path.join(OUTPUT_DIR, f"weird_fact_{data['id']}.mp4")
    render_fact_video(data, audio_path, vid_path)
    
    mgr.save_history(data['id'])
    
    if os.path.exists(audio_path): 
        os.remove(audio_path)
    for f in os.listdir(CACHE_DIR): 
        fp = os.path.join(CACHE_DIR, f)
        if os.path.isfile(fp): 
            os.remove(fp)

if __name__ == "__main__":
    main()