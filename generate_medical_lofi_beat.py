import numpy as np
import wave

sample_rate = 44100
duration = 55.0  # seconds
num_samples = int(sample_rate * duration)

bpm = 72  # Healthy resting heart rate pulse
beat_dur = 60.0 / bpm  # ~0.833s per beat

t = np.linspace(0, duration, num_samples, endpoint=False)

audio = np.zeros((num_samples, 2), dtype=np.float32)

print("Synthesizing light medically-aware clinical pulse beat...")

# 1. Heartbeat Pulse ("Lub-Dub" Cardiac Rhythm)
print("Synthesizing cardiac pulse monitor rhythm...")
num_beats = int(duration / beat_dur)
for b in range(num_beats):
    t_start = b * beat_dur
    
    # "Lub" (First heart sound S1)
    s1_idx = int(t_start * sample_rate)
    s1_len = int(0.12 * sample_rate)
    if s1_idx + s1_len < num_samples:
        k_t = np.linspace(0, 0.12, s1_len)
        freq_env = 80.0 * np.exp(-k_t * 30.0) + 35.0
        phase = 2 * np.pi * np.cumsum(freq_env) / sample_rate
        lub = np.sin(phase) * np.exp(-k_t * 18.0) * 0.45
        audio[s1_idx:s1_idx+s1_len, 0] += lub
        audio[s1_idx:s1_idx+s1_len, 1] += lub

    # "Dub" (Second heart sound S2 ~0.15s after S1)
    s2_idx = int((t_start + 0.15) * sample_rate)
    s2_len = int(0.10 * sample_rate)
    if s2_idx + s2_len < num_samples:
        k_t = np.linspace(0, 0.10, s2_len)
        freq_env = 95.0 * np.exp(-k_t * 35.0) + 40.0
        phase = 2 * np.pi * np.cumsum(freq_env) / sample_rate
        dub = np.sin(phase) * np.exp(-k_t * 22.0) * 0.35
        audio[s2_idx:s2_idx+s2_len, 0] += dub
        audio[s2_idx:s2_idx+s2_len, 1] += dub

# 2. Light Clinical Monitor Chimes (E Major / C# Minor Scale)
print("Synthesizing clinical monitor chime melodies...")
chime_freqs = [329.63, 415.30, 493.88, 554.37, 659.25, 830.61]  # E4, G#4, B4, C#5, E5, G#5
for b in range(num_beats):
    if b % 2 == 0:
        # Play a subtle chime sequence
        seq = [chime_freqs[b % len(chime_freqs)], chime_freqs[(b + 2) % len(chime_freqs)]]
        for idx, freq in enumerate(seq):
            c_start = b * beat_dur + idx * (beat_dur * 0.4)
            s_idx = int(c_start * sample_rate)
            c_len = int(0.6 * sample_rate)
            if s_idx + c_len < num_samples:
                c_t = np.linspace(0, 0.6, c_len)
                # Soft sine chime with bell-like decay
                chime = np.sin(2 * np.pi * freq * c_t) * np.exp(-c_t * 5.0) * 0.18
                # Add 2nd harmonic
                chime += np.sin(2 * np.pi * freq * 2 * c_t) * np.exp(-c_t * 8.0) * 0.06
                audio[s_idx:s_idx+c_len, 0] += chime
                audio[s_idx:s_idx+c_len, 1] += chime

# 3. Ambient Medical Pad (Light, Clean Ethereal Background Warmth)
print("Synthesizing ambient medical pad...")
pad_freqs = [164.81, 246.94, 329.63]  # E3, B3, E4
pad_signal = np.zeros(num_samples, dtype=np.float32)
for f in pad_freqs:
    lfo = 1.0 + 0.002 * np.sin(2 * np.pi * 0.2 * t)
    pad_signal += (np.sin(2 * np.pi * f * lfo * t) + 0.2 * np.sin(2 * np.pi * f * 2 * lfo * t)) * 0.08

audio[:, 0] += pad_signal
audio[:, 1] += pad_signal

# Normalize audio
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = (audio / max_val) * 0.85

audio_int16 = (audio * 32767).astype(np.int16)
wav_file = 'medical_beat.wav'
with wave.open(wav_file, 'w') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio_int16.tobytes())

print(f"Medical beat generation complete! Saved: {wav_file}")
