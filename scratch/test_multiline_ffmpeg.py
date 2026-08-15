import subprocess
import os

font_path = "C:/Windows/Fonts/Nirmala.ttc"
font_path_escaped = font_path.replace(":", "\\:")

wrapped_hi = "दिव्य दर्शनम् डेली में आपका स्वागत है।\nआज हम भगवान शिव के गले में वासुकी\nनाग के धारण करने का रहस्य जानेंगे।"
os.makedirs("scratch", exist_ok=True)
with open("scratch/multiline_hi.txt", "w", encoding="utf-8") as f:
    f.write(wrapped_hi)

filter_str = (
    f"drawtext=fontfile='{font_path_escaped}':textfile='scratch/multiline_hi.txt':"
    f"fontsize=42:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=12:"
    f"line_spacing=10:x=(w-text_w)/2:y=h*0.72"
)

cmd = [
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1080x1920:d=2',
    '-vf', filter_str,
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', 'scratch/test_multiline.mp4'
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("FFmpeg multiline drawtext returncode:", res.returncode)
if res.returncode != 0:
    print("Stderr:", res.stderr)
