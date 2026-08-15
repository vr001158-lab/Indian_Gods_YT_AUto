"""
Phase 6.3 — Acoustic Indian Devotional Music Composer
Composes a rich, authentic 60-second Indian devotional background track:
"Shiva Kailash Raga Shivaranjani Bansuri & Tanpura"

Features:
- Raga Shivaranjani melodic flute (Bansuri) with Meend pitch glides & breath dynamics
- Plucked Tanpura acoustic drone (136.1 Hz C# Om root + 5th Pa harmonic)
- Resonant Temple Bell chimes (Ghanta)
- 48 kHz stereo 16-bit PCM WAV output
"""

import math
import wave
import struct
import numpy as np
from pathlib import Path
import hashlib
import json

SAMPLE_RATE = 48000
DURATION = 60.0
NUM_SAMPLES = int(SAMPLE_RATE * DURATION)
t = np.linspace(0, DURATION, NUM_SAMPLES, endpoint=False)

# Root frequency: C# (136.1 Hz — Sacred Om frequency)
F0 = 136.10

# Raga Shivaranjani scale frequencies (Hz)
# Sa: 136.1, Re: 152.8, Ga (komal/shuddha): 163.2, Pa: 204.15, Dha: 228.9
SA  = F0
RE  = F0 * (9/8)       # 153.11 Hz
GA  = F0 * (6/5)       # 163.32 Hz (komal ga - classic Shivaranjani)
PA  = F0 * (3/2)       # 204.15 Hz
DHA = F0 * (5/3)       # 226.83 Hz
SA2 = F0 * 2.0         # 272.20 Hz
RE2 = RE * 2.0         # 306.22 Hz
GA2 = GA * 2.0         # 326.64 Hz
PA2 = PA * 2.0         # 408.30 Hz

# --- 1. Tanpura Acoustic Drone (Sa - Pa - Sa2 - Sa) ---
tanpura = np.zeros(NUM_SAMPLES, dtype=np.float32)

def pluck_string(freq, start_time, decay=2.5, amp=0.15):
    idx_start = int(start_time * SAMPLE_RATE)
    dur_samples = int(decay * SAMPLE_RATE)
    idx_end = min(NUM_SAMPLES, idx_start + dur_samples)
    t_pluck = t[idx_start:idx_end] - start_time
    
    # Rich harmonic spectrum of Tanpura (fundamental + 8 harmonics)
    env = np.exp(-1.5 * t_pluck / decay) * amp
    signal = np.zeros_like(t_pluck)
    harmonics = [1.0, 0.6, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05]
    for h_idx, h_amp in enumerate(harmonics, start=1):
        # subtle pitch modulation for jawari bridge resonance
        jawari = 1.0 + 0.002 * np.sin(2 * np.pi * 3.5 * t_pluck)
        signal += h_amp * np.sin(2 * np.pi * (freq * h_idx) * jawari * t_pluck)
    return idx_start, idx_end, signal * env

# Pluck cycle every 2.5 seconds (Sa, Pa, Sa2, Sa)
pluck_seq = [PA, SA2, SA2, SA]
cycle_len = 2.5
for i in range(int(DURATION / cycle_len)):
    st = i * cycle_len
    freq = pluck_seq[i % len(pluck_seq)]
    i_start, i_end, sig = pluck_string(freq, st, decay=2.8, amp=0.12)
    tanpura[i_start:i_end] += sig[:i_end-i_start]

# Continuous low Om drone background layer
om_drone = 0.08 * np.sin(2 * np.pi * SA * t) + 0.04 * np.sin(2 * np.pi * PA * t) + 0.02 * np.sin(2 * np.pi * (SA*2) * t)
tanpura += om_drone

# --- 2. Bansuri Flute Melodic Composition (Raga Shivaranjani) ---
flute = np.zeros(NUM_SAMPLES, dtype=np.float32)

def generate_flute_note(freq_start, freq_end, start_time, duration, amp=0.18):
    idx_start = int(start_time * SAMPLE_RATE)
    dur_samples = int(duration * SAMPLE_RATE)
    idx_end = min(NUM_SAMPLES, idx_start + dur_samples)
    t_note = t[idx_start:idx_end] - start_time
    
    # Smooth pitch glide (Meend)
    freq = np.linspace(freq_start, freq_end, len(t_note))
    
    # Envelope: soft attack, steady sustain, gentle decay
    attack = int(0.15 * SAMPLE_RATE)
    release = int(0.20 * SAMPLE_RATE)
    sustain = len(t_note) - attack - release
    
    env = np.ones(len(t_note))
    if attack > 0 and len(env) >= attack:
        env[:attack] = np.sin(np.linspace(0, np.pi/2, attack))
    if release > 0 and len(env) >= release:
        env[-release:] = np.cos(np.linspace(0, np.pi/2, release))
        
    # Flute acoustics: fundamental + soft 2nd & 3rd harmonics + subtle vibrato (5 Hz)
    vibrato = 1.0 + 0.006 * np.sin(2 * np.pi * 5.0 * t_note)
    phase = 2 * np.pi * np.cumsum(freq * vibrato) / SAMPLE_RATE
    
    tone = (
        0.8 * np.sin(phase) +
        0.3 * np.sin(2 * phase) +
        0.1 * np.sin(3 * phase)
    )
    
    # Soft breath wind noise filter
    breath = 0.02 * np.random.randn(len(t_note))
    
    sig = (tone + breath) * env * amp
    return idx_start, idx_end, sig

# Shivaranjani Flute Phrase Sequence (times in seconds)
flute_phrases = [
    # (start_freq, end_freq, start_sec, dur_sec)
    (SA2, SA2, 1.0, 3.0),
    (SA2, RE2, 4.2, 2.5),
    (RE2, GA2, 7.0, 3.5),
    (GA2, PA2, 11.0, 4.0),
    (PA2, DHA*2, 15.5, 3.0),
    (DHA*2, PA2, 19.0, 3.5),
    (PA2, GA2, 23.0, 4.0),
    (GA2, RE2, 27.5, 3.5),
    (RE2, SA2, 31.5, 4.5),
    # Second octave expressive ascent
    (SA2, GA2, 36.5, 3.0),
    (GA2, PA2, 40.0, 3.5),
    (PA2, SA2*2, 44.0, 4.0),
    (SA2*2, PA2, 48.5, 3.5),
    (PA2, GA2, 52.5, 3.0),
    (GA2, SA2, 56.0, 3.5),
]

for f_start, f_end, s_time, d_sec in flute_phrases:
    i_s, i_e, sig = generate_flute_note(f_start, f_end, s_time, d_sec)
    flute[i_s:i_e] += sig[:i_e-i_s]

# --- 3. Temple Bell (Ghanta / Chimes) ---
bells = np.zeros(NUM_SAMPLES, dtype=np.float32)

def strike_bell(start_time, freq=544.4, amp=0.10):
    idx_start = int(start_time * SAMPLE_RATE)
    decay = 4.0
    dur_samples = int(decay * SAMPLE_RATE)
    idx_end = min(NUM_SAMPLES, idx_start + dur_samples)
    t_b = t[idx_start:idx_end] - start_time
    
    # Inharmonic metallic partials
    sig = (
        1.00 * np.sin(2 * np.pi * freq * t_b) +
        0.50 * np.sin(2 * np.pi * (freq * 2.76) * t_b) +
        0.25 * np.sin(2 * np.pi * (freq * 5.40) * t_b) +
        0.15 * np.sin(2 * np.pi * (freq * 8.90) * t_b)
    )
    env = np.exp(-2.0 * t_b / decay) * amp
    return idx_start, idx_end, sig * env

bell_times = [0.5, 12.0, 24.0, 36.0, 48.0, 58.0]
for bt in bell_times:
    i_s, i_e, sig = strike_bell(bt)
    bells[i_s:i_e] += sig[:i_e-i_s]

# --- 4. Master Mix & Reverb Ambient Spatialization ---
mix_mono = tanpura + flute + bells

# Fade in / fade out
fade_in = np.sin(np.linspace(0, np.pi/2, int(2.0 * SAMPLE_RATE)))
fade_out = np.cos(np.linspace(0, np.pi/2, int(3.0 * SAMPLE_RATE)))
mix_mono[:len(fade_in)] *= fade_in
mix_mono[-len(fade_out):] *= fade_out

# Simple stereo spatial delay (left/right panning & Haas effect)
stereo_left  = mix_mono + 0.3 * np.roll(flute, int(0.015 * SAMPLE_RATE))
stereo_right = mix_mono + 0.3 * np.roll(tanpura, int(0.020 * SAMPLE_RATE))

# Normalize master peak to -3.0 dBFS
max_peak = max(np.max(np.abs(stereo_left)), np.max(np.abs(stereo_right)))
if max_peak > 0:
    target_scale = (10 ** (-3.0 / 20.0)) / max_peak
    stereo_left  *= target_scale
    stereo_right *= target_scale

# Convert to 16-bit integer PCM
audio_l_int = np.clip(stereo_left * 32767, -32768, 32767).astype(np.int16)
audio_r_int = np.clip(stereo_right * 32767, -32768, 32767).astype(np.int16)

# Interleave stereo
stereo_interleaved = np.empty((NUM_SAMPLES * 2,), dtype=np.int16)
stereo_interleaved[0::2] = audio_l_int
stereo_interleaved[1::2] = audio_r_int

out_path = Path("assets/music/devotional/shiva_devotional_shivaranjani_flute.wav")
out_path.parent.mkdir(parents=True, exist_ok=True)

with wave.open(str(out_path), "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(stereo_interleaved.tobytes())

sha256_val = hashlib.sha256(out_path.read_bytes()).hexdigest()
size_bytes = out_path.stat().st_size

print(f"[OK] Generated acoustic devotional track: {out_path}")
print(f"  Size: {size_bytes:,} bytes | SHA256: {sha256_val}")

# Update assets/music/music_manifest.json with verified provenance
manifest_path = Path("assets/music/music_manifest.json")
manifest_data = {
  "tracks": [
    {
      "filename": "shiva_devotional_shivaranjani_flute.wav",
      "relative_path": "assets/music/devotional/shiva_devotional_shivaranjani_flute.wav",
      "track_name": "Shiva Kailash Raga Shivaranjani Bansuri & Tanpura",
      "deity_relevance": "Lord Shiva / Samudra Manthan / Contemplative Divine Dharshanam",
      "category": "devotional",
      "style": "Raga Shivaranjani Bamboo Flute (Bansuri), Tanpura Drone (136.1Hz Om), Temple Bell",
      "source": "Synthesized acoustic modal composition (Raga Shivaranjani scale modeling)",
      "source_url": "internal://assets/music/devotional/shiva_devotional_shivaranjani_flute.wav",
      "license": "original/generated",
      "attribution_requirement": "None",
      "source_type": "original_generated",
      "commercial_use": True,
      "external_source": False,
      "copyright_source": "none",
      "generator": "Acoustic Modal Synthesizer (Bansuri, Tanpura, Ghanta Bell)",
      "approved": True,
      "sha256": sha256_val,
      "file_size_bytes": size_bytes,
      "duration_seconds": 60.0,
      "sample_rate": 48000,
      "channels": 2,
      "codec_name": "pcm_s16le",
      "date_selected": "2026-08-14"
    }
  ]
}

manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[OK] Updated music_manifest.json with new acoustic devotional track provenance.")
