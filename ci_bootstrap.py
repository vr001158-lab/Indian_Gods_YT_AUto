import os
import wave
import struct
import json
import hashlib
import numpy as np
from pathlib import Path
from PIL import Image

CANONICAL_ASSET_PLAN_SHA256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"
CANONICAL_MUSIC_SHA256 = "dc529b821c5d236ec450c5462dba7810c6dddb4032e6f288a59b62dba0b04e7b"

# Exact canonical byte content of data/visuals/asset_plan_20260814_071510.json
# SHA256: f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33
CANONICAL_ASSET_PLAN_BYTES = (
    b'{\n'
    b'  "topic": "Secrets of Shiva\'s Snake: The Mastery Over Ego and Poison",\n'
    b'  "deity": "lord_shiva",\n'
    b'  "created_at": "2026-08-14T07:15:10.915458+00:00",\n'
    b'  "approval_metadata": {\n'
    b'    "approved_for_generation": true,\n'
    b'    "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",\n'
    b'    "score": 66,\n'
    b'    "confidence": "high",\n'
    b'    "data_source": "youtube_api",\n'
    b'    "category": "Stories of deities"\n'
    b'  },\n'
    b'  "scenes": [\n'
    b'    {\n'
    b'      "scene": 1,\n'
    b'      "asset_type": "image",\n'
    b'      "asset": "assets/gods/lord_shiva/#shiva #shivratri #shivling #shivshankar #mahadev.jpg",\n'
    b'      "asset_id": "#shiva #shivratri #shivling #shivshankar #mahadev",\n'
    b'      "deity": "lord_shiva",\n'
    b'      "source": "repository",\n'
    b'      "reason_for_selection": "Semantic match (score=2) in repository deity assets for \'lord_shiva\'",\n'
    b'      "validation_result": "OK"\n'
    b'    },\n'
    b'    {\n'
    b'      "scene": 2,\n'
    b'      "asset_type": "image",\n'
    b'      "asset": "assets/gods/lord_shiva/Divine Trident of Cosmic Power\xe2\x9a\xa1\xef\xb8\x8f\xf0\x9f\x94\x91 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy.jpg",\n'
    b'      "asset_id": "Divine Trident of Cosmic Power\xe2\x9a\xa1\xef\xb8\x8f\xf0\x9f\x94\x91 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy",\n'
    b'      "deity": "lord_shiva",\n'
    b'      "source": "repository",\n'
    b'      "reason_for_selection": "Semantic match (score=1) in repository deity assets for \'lord_shiva\'",\n'
    b'      "validation_result": "OK"\n'
    b'    },\n'
    b'    {\n'
    b'      "scene": 3,\n'
    b'      "asset_type": "image",\n'
    b'      "asset": "assets/gods/lord_shiva/Divine Trident of Cosmic Power\xe2\x9a\xa1\xef\xb8\x8f\xf0\x9f\x94\x91 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy.jpg",\n'
    b'      "asset_id": "Divine Trident of Cosmic Power\xe2\x9a\xa1\xef\xb8\x8f\xf0\x9f\x94\x91 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy",\n'
    b'      "deity": "lord_shiva",\n'
    b'      "source": "repository",\n'
    b'      "reason_for_selection": "Semantic match (score=3) in repository deity assets for \'lord_shiva\'",\n'
    b'      "validation_result": "OK"\n'
    b'    },\n'
    b'    {\n'
    b'      "scene": 4,\n'
    b'      "asset_type": "image",\n'
    b'      "asset": "assets/gods/lord_shiva/#shiva #shivratri #shivling #shivshankar #mahadev.jpg",\n'
    b'      "asset_id": "#shiva #shivratri #shivling #shivshankar #mahadev",\n'
    b'      "deity": "lord_shiva",\n'
    b'      "source": "repository",\n'
    b'      "reason_for_selection": "Semantic match (score=2) in repository deity assets for \'lord_shiva\'",\n'
    b'      "validation_result": "OK"\n'
    b'    },\n'
    b'    {\n'
    b'      "scene": 5,\n'
    b'      "asset_type": "image",\n'
    b'      "asset": "assets/gods/lord_shiva/181199585004244858.jpg",\n'
    b'      "asset_id": "181199585004244858",\n'
    b'      "deity": "lord_shiva",\n'
    b'      "source": "repository",\n'
    b'      "reason_for_selection": "Deity repository asset fallback for \'lord_shiva\' (scene #5)",\n'
    b'      "validation_result": "OK"\n'
    b'    }\n'
    b'  ]\n'
    b'}'
)


def generate_canonical_shiva_music(out_path: Path):
    """
    Synthesizes the exact deterministic 60-second acoustic devotional track:
    'Shiva Kailash Raga Shivaranjani Bansuri & Tanpura'
    Produces exact SHA256: dc529b821c5d236ec450c5462dba7810c6dddb4032e6f288a59b62dba0b04e7b
    """
    np.random.seed(42)
    sample_rate = 48000
    duration = 60.0
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    F0 = 136.10
    SA  = F0
    RE  = F0 * (9/8)
    GA  = F0 * (6/5)
    PA  = F0 * (3/2)
    DHA = F0 * (5/3)
    SA2 = F0 * 2.0
    RE2 = RE * 2.0
    GA2 = GA * 2.0
    PA2 = PA * 2.0

    tanpura = np.zeros(num_samples, dtype=np.float32)

    def pluck_string(freq, start_time, decay=2.5, amp=0.15):
        idx_start = int(start_time * sample_rate)
        dur_samples = int(decay * sample_rate)
        idx_end = min(num_samples, idx_start + dur_samples)
        t_pluck = t[idx_start:idx_end] - start_time
        env = np.exp(-1.5 * t_pluck / decay) * amp
        signal = np.zeros_like(t_pluck)
        harmonics = [1.0, 0.6, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05]
        for h_idx, h_amp in enumerate(harmonics, start=1):
            jawari = 1.0 + 0.002 * np.sin(2 * np.pi * 3.5 * t_pluck)
            signal += h_amp * np.sin(2 * np.pi * (freq * h_idx) * jawari * t_pluck)
        return idx_start, idx_end, signal * env

    pluck_seq = [PA, SA2, SA2, SA]
    cycle_len = 2.5
    for i in range(int(duration / cycle_len)):
        st = i * cycle_len
        freq = pluck_seq[i % len(pluck_seq)]
        i_start, i_end, sig = pluck_string(freq, st, decay=2.8, amp=0.12)
        tanpura[i_start:i_end] += sig[:i_end-i_start]

    om_drone = 0.08 * np.sin(2 * np.pi * SA * t) + 0.04 * np.sin(2 * np.pi * PA * t) + 0.02 * np.sin(2 * np.pi * (SA*2) * t)
    tanpura += om_drone

    flute = np.zeros(num_samples, dtype=np.float32)

    def generate_flute_note(freq_start, freq_end, start_time, dur_sec, amp=0.18):
        idx_start = int(start_time * sample_rate)
        dur_samples = int(dur_sec * sample_rate)
        idx_end = min(num_samples, idx_start + dur_samples)
        t_note = t[idx_start:idx_end] - start_time
        freq = np.linspace(freq_start, freq_end, len(t_note))
        attack = int(0.15 * sample_rate)
        release = int(0.20 * sample_rate)
        env = np.ones(len(t_note))
        if attack > 0 and len(env) >= attack:
            env[:attack] = np.sin(np.linspace(0, np.pi/2, attack))
        if release > 0 and len(env) >= release:
            env[-release:] = np.cos(np.linspace(0, np.pi/2, release))
        vibrato = 1.0 + 0.006 * np.sin(2 * np.pi * 5.0 * t_note)
        phase = 2 * np.pi * np.cumsum(freq * vibrato) / sample_rate
        tone = 0.8 * np.sin(phase) + 0.3 * np.sin(2 * phase) + 0.1 * np.sin(3 * phase)
        breath = 0.02 * np.random.randn(len(t_note))
        sig = (tone + breath) * env * amp
        return idx_start, idx_end, sig

    flute_phrases = [
        (SA2, SA2, 1.0, 3.0), (SA2, RE2, 4.2, 2.5), (RE2, GA2, 7.0, 3.5),
        (GA2, PA2, 11.0, 4.0), (PA2, DHA*2, 15.5, 3.0), (DHA*2, PA2, 19.0, 3.5),
        (PA2, GA2, 23.0, 4.0), (GA2, RE2, 27.5, 3.5), (RE2, SA2, 31.5, 4.5),
        (SA2, GA2, 36.5, 3.0), (GA2, PA2, 40.0, 3.5), (PA2, SA2*2, 44.0, 4.0),
        (SA2*2, PA2, 48.5, 3.5), (PA2, GA2, 52.5, 3.0), (GA2, SA2, 56.0, 3.5),
    ]

    for f_start, f_end, s_time, d_sec in flute_phrases:
        i_s, i_e, sig = generate_flute_note(f_start, f_end, s_time, d_sec)
        flute[i_s:i_e] += sig[:i_e-i_s]

    bells = np.zeros(num_samples, dtype=np.float32)

    def strike_bell(start_time, freq=544.4, amp=0.10):
        idx_start = int(start_time * sample_rate)
        decay = 4.0
        dur_samples = int(decay * sample_rate)
        idx_end = min(num_samples, idx_start + dur_samples)
        t_b = t[idx_start:idx_end] - start_time
        sig = (
            1.00 * np.sin(2 * np.pi * freq * t_b) +
            0.50 * np.sin(2 * np.pi * (freq * 2.76) * t_b) +
            0.25 * np.sin(2 * np.pi * (freq * 5.40) * t_b) +
            0.15 * np.sin(2 * np.pi * (freq * 8.90) * t_b)
        )
        env = np.exp(-2.0 * t_b / decay) * amp
        return idx_start, idx_end, sig * env

    for bt in [0.5, 12.0, 24.0, 36.0, 48.0, 58.0]:
        i_s, i_e, sig = strike_bell(bt)
        bells[i_s:i_e] += sig[:i_e-i_s]

    mix_mono = tanpura + flute + bells
    fade_in = np.sin(np.linspace(0, np.pi/2, int(2.0 * sample_rate)))
    fade_out = np.cos(np.linspace(0, np.pi/2, int(3.0 * sample_rate)))
    mix_mono[:len(fade_in)] *= fade_in
    mix_mono[-len(fade_out):] *= fade_out

    stereo_left  = mix_mono + 0.3 * np.roll(flute, int(0.015 * sample_rate))
    stereo_right = mix_mono + 0.3 * np.roll(tanpura, int(0.020 * sample_rate))

    max_peak = max(np.max(np.abs(stereo_left)), np.max(np.abs(stereo_right)))
    if max_peak > 0:
        target_scale = (10 ** (-3.0 / 20.0)) / max_peak
        stereo_left  *= target_scale
        stereo_right *= target_scale

    audio_l_int = np.clip(stereo_left * 32767, -32768, 32767).astype(np.int16)
    audio_r_int = np.clip(stereo_right * 32767, -32768, 32767).astype(np.int16)

    stereo_interleaved = np.empty((num_samples * 2,), dtype=np.int16)
    stereo_interleaved[0::2] = audio_l_int
    stereo_interleaved[1::2] = audio_r_int

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo_interleaved.tobytes())


def bootstrap():
    """Generates minimal deterministic test fixtures for clean CI runners."""

    # 1. Create minimal valid 1280x720 PNG thumbnail and metadata
    thumb_dir = Path("data/thumbnails")
    thumb_dir.mkdir(parents=True, exist_ok=True)

    thumb_png = thumb_dir / "thumbnail_20260814_071510.png"
    if not thumb_png.exists():
        img = Image.new("RGB", (1280, 720), color=(20, 25, 40))
        img.save(thumb_png, format="PNG")
        print(f"[CI BOOTSTRAP] Thumbnail created: {thumb_png}")

    thumb_meta = thumb_dir / "thumbnail_metadata_20260814_071510.json"
    if not thumb_meta.exists():
        meta_data = {
            "created_at": "20260814_071510",
            "format": "png",
            "width": 1280,
            "height": 720,
            "topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "provider": "pil"
        }
        thumb_meta.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
        print(f"[CI BOOTSTRAP] Thumbnail metadata created: {thumb_meta}")

    # 2. Canonical visual asset plan fixture (data/visuals/asset_plan_20260814_071510.json)
    visuals_dir = Path("data/visuals")
    visuals_dir.mkdir(parents=True, exist_ok=True)
    asset_plan_file = visuals_dir / "asset_plan_20260814_071510.json"

    if asset_plan_file.exists() and hashlib.sha256(asset_plan_file.read_bytes()).hexdigest() == CANONICAL_ASSET_PLAN_SHA256:
        print("Canonical asset plan exists, skipping creation")
    else:
        asset_plan_file.write_bytes(CANONICAL_ASSET_PLAN_BYTES)
        print(f"[CI BOOTSTRAP] Asset plan created: {asset_plan_file}")

    # 3. Deterministic WAV music fixture (assets/music/devotional/ & data/music/)
    # NOTE: Does NOT mutate production assets/music/music_manifest.json
    music_paths = [
        Path("assets/music/devotional/shiva_devotional_shivaranjani_flute.wav"),
        Path("data/music/shiva_devotional_shivaranjani_flute.wav"),
    ]

    for mpath in music_paths:
        mpath.parent.mkdir(parents=True, exist_ok=True)
        needs_gen = not mpath.exists()
        if not needs_gen:
            curr_sha = hashlib.sha256(mpath.read_bytes()).hexdigest()
            if curr_sha != CANONICAL_MUSIC_SHA256:
                needs_gen = True

        if needs_gen:
            generate_canonical_shiva_music(mpath)
            actual_sha = hashlib.sha256(mpath.read_bytes()).hexdigest()
            assert actual_sha == CANONICAL_MUSIC_SHA256, f"WAV SHA256 mismatch! Got {actual_sha}, expected {CANONICAL_MUSIC_SHA256}"
            print(f"[CI BOOTSTRAP] Canonical WAV created: {mpath}")

if __name__ == "__main__":
    bootstrap()
