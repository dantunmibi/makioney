import os
import json
import random
import requests
import subprocess
import time
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

if not os.path.exists(FONT_PATH): 
    FONT_PATH = "DejaVu-Sans-Bold"

for d in [DATA_DIR, OUTPUT_DIR, CACHE_DIR]: 
    os.makedirs(d, exist_ok=True)

# --- MODULE 1: CONTENT (r/TwoSentenceHorror) ---
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
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            time.sleep(random.uniform(1, 3))
            
            urls = [
                "https://old.reddit.com/r/TwoSentenceHorror/top.json?t=day&limit=20",
                "https://www.reddit.com/r/TwoSentenceHorror/.json?limit=20",
            ]
            
            for url in urls:
                try:
                    r = requests.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        
                        for post in data['data']['children']:
                            p = post['data']
                            if p['id'] not in self.history and not p['over_18']:
                                return {
                                    "id": p['id'],
                                    "setup": p['title'],
                                    "punchline": p['selftext']
                                }
                        break
                except Exception as e:
                    print(f"⚠️ URL {url} failed: {e}")
                    continue
        except Exception as e:
            print(f"⚠️ Scrape failed: {e}")
        
        return {
            "id": f"backup_{random.randint(1000,9999)}",
            "setup": "I heard my mom calling me into the kitchen.",
            "punchline": "As I ran down the hall, she whispered from the closet, 'Don't go, I heard it too.'"
        }

# --- MODULE 2: SCARY VISUALS ---
class HorrorAssetGen:
    def get_creepy_image(self, prompt):
        horror_prompt = f"horror photography, grainy, vintage, dark atmosphere, scary, {prompt}"
        encoded = requests.utils.quote(horror_prompt)
        filename = os.path.join(CACHE_DIR, f"scary_{abs(hash(prompt))}.jpg")
        
        apis = [
            f"https://pollinations.ai/p/{encoded}?width=1080&height=1920&nologo=true&enhance=true",
            f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true",
        ]
        
        for api_url in apis:
            try:
                print(f"🎨 Generating Horror Art: {prompt[:20]}...")
                r = requests.get(api_url, timeout=45, stream=True)
                
                if r.status_code == 200:
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    if os.path.exists(filename) and os.path.getsize(filename) > 5000:
                        print(f"✅ Horror image generated")
                        return filename
            except Exception as e:
                print(f"⚠️ API failed: {e}")
                continue
        
        return None

# --- MODULE 3: AUDIO ---
def generate_scary_voice(text, filename):
    try:
        print("🎤 Generating scary voice with Kokoro...")
        import kokoro
        import numpy as np
        
        pipeline = kokoro.KPipeline(lang_code="en-us")
        
        audio_chunks = []
        for chunk in pipeline(text, voice="am_adam"):
            if isinstance(chunk, np.ndarray):
                audio_chunks.append(chunk.flatten())
            else:
                audio_chunks.append(np.array(chunk).flatten())
        
        audio_array = np.concatenate(audio_chunks)
        
        if audio_array.dtype != np.int16:
            audio_array = (audio_array * 32767).astype(np.int16)
        
        import scipy.io.wavfile as wav
        temp_wav = filename.replace('.mp3', '_temp.wav')
        wav.write(temp_wav, 24000, audio_array)
        
        subprocess.run([
            'ffmpeg', '-i', temp_wav,
            '-af', 'asetrate=24000*0.9,atempo=1.11,aresample=24000',
            '-codec:a', 'libmp3lame', '-qscale:a', '2',
            '-y', filename
        ], check=True, capture_output=True, stderr=subprocess.PIPE)
        
        if os.path.exists(temp_wav): 
            os.remove(temp_wav)
        
        print(f"✅ Scary audio generated")
        
    except Exception as e:
        print(f"⚠️ Kokoro failed ({e}), using gTTS...")
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=True)
        tts.save(filename)
        print(f"✅ Audio saved with gTTS")

# --- MODULE 4: RENDER ENGINE ---
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