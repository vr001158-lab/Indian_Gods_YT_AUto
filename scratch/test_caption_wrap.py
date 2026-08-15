import os
import subprocess
from pathlib import Path

def wrap_text(text: str, max_chars: int = 35) -> str:
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        if current_len + len(w) + (1 if current_line else 0) <= max_chars:
            current_line.append(w)
            current_len += len(w) + (1 if current_len > 0 else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)

hindi_text = "दिव्य दर्शनम् डेली में आपका स्वागत है। आज हम भगवान शिव के गले में वासुकी नाग के धारण करने का रहस्य जानेंगे।"
wrapped = wrap_text(hindi_text)
print("Wrapped Hindi text:")
print(wrapped)

os.makedirs("scratch", exist_ok=True)
caption_file = Path("scratch/caption_hi.txt")
caption_file.write_text(wrapped, encoding="utf-8")

print("\nSaved caption file.")
