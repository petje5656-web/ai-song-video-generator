import os
import sys
import json
from gradio_client import Client
import shutil
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play
import numpy as np
from scipy import signal

print("=" * 60)
print("🎵 SONG GENERATION STARTING")
print("=" * 60)

if not os.path.exists("structured_lyrics.txt"):
    print("❌ Error: structured_lyrics.txt not found!")
    print("Run fetch_lyrics.py first to generate lyrics.")
    sys.exit(1)

with open("structured_lyrics.txt", 'r', encoding='utf-8') as f:
    lyrics = f.read()

if not lyrics.strip():
    print("❌ Error: structured_lyrics.txt is empty!")
    sys.exit(1)

# Read metadata from lyrics_metadata.json if available
if os.path.exists('lyrics_metadata.json'):
    with open('lyrics_metadata.json', 'r') as f:
        metadata = json.load(f)
        title = metadata.get('title', 'Hey Jude')
        artist = metadata.get('artist', 'The Beatles')
else:
    # Fallback to environment variables or defaults
    title = os.getenv('SONG_TITLE', 'Hey Jude')
    artist = os.getenv('SONG_ARTIST', 'The Beatles')

print(f"\n🎤 Song: '{title}' by {artist}")
print("🎧 Style: Lofi pop, slowed reverb")
print("⏳ Connecting to AI music generator...\n")

try:
    client = Client("tencent/SongGeneration")
    print("✓ Connected to Gradio API\n")
except Exception as e:
    print(f"❌ Error connecting to API: {e}")
    sys.exit(1)

print("⏳ Generating song (this may take 2-5 minutes)...\n")

try:
    result = client.predict(
        lyric=lyrics,
        description=f"Female Voice, piano, guitar and drums, the bpm is 90, Lofi, chill beats, mellow, dreamy",
        prompt_audio=None,
        genre="Auto",
        cfg_coef=1.5,
        temperature=0.8,
        api_name="/generate_song"
    )
    print(result) 
except Exception as e:
    print(f"❌ Error generating song: {e}")
    sys.exit(1)

if isinstance(result, (list, tuple)) and len(result) >= 2:
    audio_path = result[0]
    gen_metadata = result[1] if isinstance(result[1], dict) else {}
else:
    audio_path = result if isinstance(result, str) else result[0]
    gen_metadata = {}

print("=" * 60)
print("✅ SONG GENERATED SUCCESSFULLY!")
print("=" * 60)
print(f"📁 Original file: {audio_path}")
if gen_metadata and 'inference_duration' in gen_metadata:
    print(f"⏱️  Generation time: {gen_metadata['inference_duration']:.1f}s")
else:
    print(f"⏱️  Generation complete")

output_filename = f"{title.replace(' ', '_').lower()}_ai_cover.flac"
lofi_filename = f"{title.replace(' ', '_').lower()}_ai_cover_lofi.flac"

print("\n🎛️  Applying lofi effects...")
print("   ├─ Slowing to 0.8x speed")
print("   ├─ Adding reverb")
print("   ├─ Lowering pitch (-2 semitones)")
print("   ├─ Adding vinyl crackle")
print("   └─ Applying low-pass filter\n")

try:
    # Load original audio
    audio = AudioSegment.from_file(audio_path)
    
    # 1. SLOW DOWN TO 0.8x (Core lofi effect)
    slowed_audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * 0.8)
    })
    slowed_audio = slowed_audio.set_frame_rate(audio.frame_rate)
    
    # 2. PITCH SHIFT DOWN (-2 semitones for that dreamy lofi feel)
    # Note: This is approximate pitch shifting using playback rate
    pitched_audio = slowed_audio._spawn(slowed_audio.raw_data, overrides={
        "frame_rate": int(slowed_audio.frame_rate * 0.887)  # ~-2 semitones
    })
    pitched_audio = pitched_audio.set_frame_rate(slowed_audio.frame_rate)
    
    # 3. LOW-PASS FILTER (Removes high frequencies for warmth)
    # Convert to numpy array for filtering
    samples = np.array(pitched_audio.get_array_of_samples())
    
    # Design low-pass filter (cutoff at ~5kHz for lofi warmth)
    nyquist = pitched_audio.frame_rate / 2
    cutoff = 5000  # Hz
    normalized_cutoff = cutoff / nyquist
    b, a = signal.butter(4, normalized_cutoff, btype='low')
    filtered_samples = signal.filtfilt(b, a, samples)
    
    # Convert back to AudioSegment
    filtered_audio = pitched_audio._spawn(filtered_samples.astype(np.int16).tobytes())
    
    # 4. ADD REVERB (Simulated with echo)
    # Add subtle echo for reverb effect
    echo_delay = 150  # ms
    echo_decay = 0.3  # 30% volume
    reverb_audio = filtered_audio.overlay(
        filtered_audio - (echo_decay * 10),  # Reduce volume in dB
        position=echo_delay
    )
    
    # Add second echo for more depth
    reverb_audio = reverb_audio.overlay(
        filtered_audio - (echo_decay * 15),
        position=echo_delay * 2
    )
    
    # 5. ADD VINYL CRACKLE (Optional subtle noise)
    # Generate very subtle noise
    duration_ms = len(reverb_audio)
    noise = AudioSegment.silent(duration=duration_ms)
    
    # Create random crackle (very low volume)
    noise_samples = np.random.normal(0, 5, len(noise.get_array_of_samples()))
    noise = noise._spawn(noise_samples.astype(np.int16).tobytes())
    
    # Mix in very quietly
    final_audio = reverb_audio.overlay(noise - 40)  # -40dB quieter
    
    # 6. SLIGHT COMPRESSION (Reduce dynamic range for consistent lofi feel)
    # This is a simple implementation - just normalize and reduce peaks
    final_audio = final_audio.normalize()
    
    # 7. REDUCE VOLUME SLIGHTLY (Lofi is often more subdued)
    final_audio = final_audio - 2  # Reduce by 2dB
    
    # Export final lofi version
    final_audio.export(lofi_filename, format="flac")
    
    # Also save original slowed version
    shutil.copy(audio_path, output_filename)
    
except Exception as e:
    print(f"❌ Error processing audio: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("✅ LOFI PROCESSING COMPLETE!")
print("=" * 60)
print(f"📁 Original (1.0x): {output_filename}")
print(f"📁 Lofi Version: {lofi_filename}")
print(f"🎵 Duration: {len(final_audio) / 1000:.2f}s")
print("\n🎛️  Effects applied:")
print("   ✓ 0.8x speed (slowed)")
print("   ✓ -2 semitones pitch")
print("   ✓ Reverb/echo")
print("   ✓ Low-pass filter (5kHz)")
print("   ✓ Vinyl crackle")
print("   ✓ Compression & normalization")
print("=" * 60)

print("\n🔊 Attempting playback (may not work in CI environment)...")
try:
    print("💪💪💪💪Done Crunching the video!") #play(final_audio[:30000])  # Play first 30 seconds
except:
    print("⚠️  Playback not available in this environment (expected in CI)")

print("\n✅ Files saved! Run create_video.py next to make the music video.")
