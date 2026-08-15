import subprocess
import os

os.makedirs('scratch', exist_ok=True)
texts = {
    'hi': 'दिव्य दर्शनम् डेली में आपका स्वागत है।',
    'te': 'దివ్య దర్శనం డైలీకి స్వాగతం.',
    'ta': 'திவ்ய தரிசனம் டெய்லிக்கு உங்களை வரவேற்கிறோம்.'
}

font_path = "C:/Windows/Fonts/Nirmala.ttc"
font_path_escaped = font_path.replace(":", "\\:")

for lang, text in texts.items():
    txt_file = f'scratch/{lang}.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)

    filter_str = (
        f"drawtext=fontfile='{font_path_escaped}':textfile='{txt_file}':"
        f"fontsize=48:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=12:"
        f"x=(w-text_w)/2:y=h*0.75"
    )

    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1080x1920:d=2',
        '-vf', filter_str,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', f'scratch/test_{lang}.mp4'
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Lang {lang} Returncode:", res.returncode)
    if res.returncode != 0:
        print("Stderr:", res.stderr)
