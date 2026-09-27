import numpy as np
import wave

sample_rate = 44100
duration = 50.0  # seconds
num_samples = int(sample_rate * duration)

bpm = 86
beat_dur = 60.0 / bpm
bar_dur = beat_dur * 4

t = np.linspace(0, duration, num_samples, endpoint=False)

def note_freq(name):
    notes = {
        'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'F3': 174.61, 'G3': 196.00, 'A3': 220.00, 'B3': 246.94,
        'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 'A4': 440.00, 'B4': 493.88
    }
    return notes.get(name, 220.0)

chords = [
    ['F3', 'A3', 'C4', 'E4'],  # Fmaj7
    ['E3', 'G3', 'B3', 'D4'],  # Em7
    ['D3', 'F3', 'A3', 'C4'],  # Dm7
    ['C3', 'E3', 'G3', 'B4']   # Cmaj7
]

audio = np.zeros((num_samples, 2), dtype=np.float32)

print("Synthesizing vectorized lo-fi chords...")
bar_indices = (t / bar_dur).astype(int)
t_in_bar = t % bar_dur
env = np.exp(-t_in_bar * 0.8) * 0.25 + 0.05
vibrato = 1.0 + 0.003 * np.sin(2 * np.pi * 4.5 * t)

chord_signal = np.zeros(num_samples, dtype=np.float32)
for b_idx, chord in enumerate(chords):
    mask = (bar_indices % len(chords)) == b_idx
    if not np.any(mask):
        continue
    sub_t = t[mask]
    sub_vib = vibrato[mask]
    sub_env = env[mask]
    val = np.zeros(np.sum(mask), dtype=np.float32)
    for note in chord:
        f = note_freq(note)
        f_mod = f * sub_vib
        w = np.sin(2 * np.pi * f_mod * sub_t) + 0.25 * np.sin(2 * np.pi * f_mod * 2 * sub_t)
        val += w * sub_env
    chord_signal[mask] = val / len(chord)

audio[:, 0] += chord_signal * 0.4
audio[:, 1] += chord_signal * 0.4

print("Synthesizing vectorized drum beats...")
num_beats = int(duration / beat_dur)
for b in range(num_beats):
    t_start = b * beat_dur
    beat_in_bar = b % 4
    
    # Kick
    k_times = [t_start]
    if beat_in_bar == 2:
        k_times.append(t_start + 0.5 * beat_dur)
    for kt in k_times:
        s_idx = int(kt * sample_rate)
        k_len = int(0.18 * sample_rate)
        if s_idx + k_len < num_samples:
            k_t = np.linspace(0, 0.18, k_len)
            freq_env = 120.0 * np.exp(-k_t * 35.0) + 40.0
            phase = 2 * np.pi * np.cumsum(freq_env) / sample_rate
            kick = np.sin(phase) * np.exp(-k_t * 15.0) * 0.6
            audio[s_idx:s_idx+k_len, 0] += kick
            audio[s_idx:s_idx+k_len, 1] += kick
            
    # Snare
    if beat_in_bar in [1, 3]:
        s_idx = int(t_start * sample_rate)
        sn_len = int(0.15 * sample_rate)
        if s_idx + sn_len < num_samples:
            sn_t = np.linspace(0, 0.15, sn_len)
            noise = np.random.uniform(-1, 1, sn_len) * np.exp(-sn_t * 22.0)
            tone = np.sin(2 * np.pi * 180.0 * sn_t) * np.exp(-sn_t * 30.0)
            snare = (noise * 0.4 + tone * 0.3) * 0.5
            audio[s_idx:s_idx+sn_len, 0] += snare
            audio[s_idx:s_idx+sn_len, 1] += snare

    # Hi-hat
    for hh in [0, 0.5]:
        ht = t_start + hh * beat_dur
        s_idx = int(ht * sample_rate)
        hh_len = int(0.05 * sample_rate)
        if s_idx + hh_len < num_samples:
            hh_t = np.linspace(0, 0.05, hh_len)
            hh_noise = np.random.uniform(-1, 1, hh_len) * np.exp(-hh_t * 80.0) * 0.15
            audio[s_idx:s_idx+hh_len, 0] += hh_noise
            audio[s_idx:s_idx+hh_len, 1] += hh_noise

print("Adding vinyl crackle...")
vinyl = np.random.normal(0, 0.01, num_samples)
audio[:, 0] += vinyl * 0.3
audio[:, 1] += vinyl * 0.3

# Normalize
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = (audio / max_val) * 0.85

audio_int16 = (audio * 32767).astype(np.int16)
wav_file = 'lofi_music.wav'
with wave.open(wav_file, 'w') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio_int16.tobytes())

print(f"Vectorized generation complete! Saved: {wav_file}")
