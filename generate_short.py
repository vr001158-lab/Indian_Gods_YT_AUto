import random
import json
import subprocess
import asyncio
import sys
from pathlib import Path

# =========================
# CONFIGURATION & PATHS
# =========================
BASE = Path("assets/horror_stories")
CLIPS = list((BASE / "clips").glob("*.mp4"))
MUSIC = list((BASE / "music").glob("*.aac")) 
SETS_FILE = BASE / "sets.txt"
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

VOICE = "en-US-ChristopherNeural" 
CHANNEL_BRAND = "@Horrorstories-mb2L"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" 

def optimize_hook(hook):
    triggers = [
        "I shouldn’t have opened it:",
        "The police never explained this:",
        "Every night it gets closer:",
        "I thought it was fake until tonight:",
        "My camera recorded something impossible:",
        "I still don’t know what was standing there:",
        "The audio gets worse at the end:",
        "I found this hidden in my apartment:",
        "This happened exactly at 3:00 AM:",
        "Nobody believes what the footage shows:",
        "I wish I never checked the recording:",
        "The last frame terrified me:",
        "I woke up to this outside my door:",
        "The mirror moved before I did:",
        "Someone was inside the house already:",
        "I heard breathing behind me:",
        "The emergency alert was real:",
        "This was recorded on a disconnected phone:",
        "I thought I was alone until this happened:",
        "The hallway was longer than before:",
        "I found this buried under my floorboards:",
        "My reflection stopped copying me:",
        "The final message wasn’t meant for me:",
        "The voice came from inside the walls:",
        "I replayed the footage and noticed this:",
        "There was something standing behind the curtain:",
        "The thing outside knew my name:",
        "I never should have answered the call:",
        "The security footage disappeared after this:",
        "The basement door opened by itself:",
        "This only happens after midnight:",
        "The radio warned me too late:",
        "I heard knocking from inside the ceiling:",
        "Nobody else could see the figure:",
        "The camera captured me sleeping… twice:",
        "The next morning the footprints were inside:",
        "Someone whispered through the baby monitor:",
        "The elevator stopped on a floor that doesn’t exist:",
        "The hidden room was already occupied:",
        "Something followed me home that night:",
        "I checked the mirror one last time:",
        "The static started saying my name:",
        "I found tomorrow’s date in my diary:",
        "The shadow moved after I stopped:",
        "The door appeared overnight:",
        "I heard my dead friend calling me:",
        "The thing under my bed answered back:",
        "I paused the video at the wrong moment:",
        "This story was removed from the police report:",
        "The final recording still exists:"
    ]

    return random.choice(triggers) + " " + hook
def load_sets(path):
    cats = {"General": []}
    cur = "General"
    if not path.exists(): return cats
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        if line.startswith("["):
            cur = line[1:-1]
            cats[cur] = []
        elif "|" in line:
            p = line.split("|")
            if len(p) >= 3: cats[cur].append({"hook": p[0].strip(), "body": p[1].strip(), "insight": p[2].strip()})
    return cats

async def tts_task(text, out_path):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(out_path)

def get_duration(file):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file)]
    return float(subprocess.check_output(cmd).decode().strip())

def run():
    ALL_SETS = load_sets(SETS_FILE)
    ALL = [x for v in ALL_SETS.values() for x in v]
    
    selected_clips = random.sample(CLIPS, min(4, len(CLIPS)))
    music_file = random.choice(MUSIC)
    pair = random.choice(ALL)

    hook = optimize_hook(pair["hook"])
    print(f"🎬 GENERATING: {hook}")

    vo_path = OUTPUT / "vo.mp3"
    full_script = f"{hook}. {pair['body']}. {pair['insight']}. Subscribe for more."
    asyncio.run(tts_task(full_script, vo_path))

    duration = get_duration(vo_path)
    sub_start = max(0, duration - 3) 

    input_cmds = []
    filter_concat = ""
    for i, c in enumerate(selected_clips):
        input_cmds.extend(["-i", str(c)])
        filter_concat += f"[{i}:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1[v{i}];"
    
    for i in range(len(selected_clips)):
        filter_concat += f"[v{i}]"
    filter_concat += f"concat=n={len(selected_clips)}:v=1:a=0[v_raw];"

    clean_hook = hook.upper().replace("'", "").replace(":", "")
    
    # Visual Effects: Hook (0-2s), Branding (static), Subscribe (last 3s)
    hook_layer = (f"drawtext=text='{clean_hook}':fontfile='{FONT_PATH}':fontcolor=yellow:fontsize=45:"
                  f"borderw=5:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2-150:enable='between(t,0,2)'")
    
    brand_layer = f"drawtext=text='{CHANNEL_BRAND}':fontfile='{FONT_PATH}':fontcolor=white@0.4:fontsize=20:x=w-tw-20:y=20"
    
    sub_layer = (f"drawtext=text='SUBSCRIBE FOR MORE':fontfile='{FONT_PATH}':fontcolor=red:fontsize=60:"
                 f"borderw=4:bordercolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='gt(t,{sub_start:.2f})'")

    video_fx = f"[v_raw]{hook_layer},{brand_layer},{sub_layer}[v]"

    # AUDIO LEVELS: Balanced for YouTube (Music < Voice)
    # 0.20 volume for music is the "sweet spot" for background ambiance
    audio_fx = f"[4:a]volume=0.20[bg];[5:a]volume=2.5[main];[bg][main]amix=inputs=2:duration=shortest[a]"
    
    output_file = OUTPUT / "short_horror.mp4"
    
    cmd = ["ffmpeg", "-y"]
    cmd.extend(input_cmds) # Clips (0-3)
    cmd.extend(["-stream_loop", "-1", "-i", str(music_file)]) # Background Music (4)
    cmd.extend(["-i", str(vo_path)]) # Voiceover (5)
    
    cmd.extend([
        "-filter_complex", f"{filter_concat}{video_fx};{audio_fx}",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{duration:.2f}", 
        str(output_file)
    ])

    subprocess.run(cmd, check=True)
    
    print(json.dumps({
        "video": str(output_file),
        "title": f"{hook} #Shorts #Horror",
        "body": pair["body"]
    }))

if __name__ == "__main__":
    run()
