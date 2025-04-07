import subprocess
import os
import sys
import shutil
import essentia
import essentia.standard as es
import csv
import json

# === STEP 1: VALIDATE INPUT ===

if len(sys.argv) < 2:
    print("❌ Error: No audio file provided.")
    sys.exit(1)

input_audio = sys.argv[1]
output_folder = "demucs_output"

# === STEP 2: PREPARE OUTPUT FOLDER ===

os.makedirs(output_folder, exist_ok=True)

base = os.path.splitext(os.path.basename(input_audio))[0]
demucs_out_path = os.path.join(output_folder, "htdemucs_6s", base)

# Clean previous output if it exists
if os.path.exists(demucs_out_path):
    shutil.rmtree(demucs_out_path)

# === STEP 3: RUN DEMUCS TO ISOLATE GUITAR ===

print("🎛️ Running Demucs to isolate guitar...")
command = [
    "demucs",
    "-n", "htdemucs_6s",
    "--two-stems", "guitar",
    input_audio,
    "--out", output_folder
]
subprocess.run(command)

# Path to isolated guitar stem
guitar_path = os.path.join(demucs_out_path, "guitar.wav")

if not os.path.exists(guitar_path):
    print("⚠️ Guitar stem not found.")
    sys.exit(1)

print("✅ Guitar-only audio ready:", guitar_path)

# === STEP 4: RUN CHORD DETECTION WITH ESSENTIA ===

print("🎶 Running chord detection on isolated guitar audio...")
audio = es.MonoLoader(filename=guitar_path)()
sample_rate = 44100
frame_size = 2048
hop_size = 128

# Pitch tracking
pitch_values, pitch_confidence = es.PredominantPitchMelodia(
    frameSize=frame_size,
    hopSize=hop_size
)(audio)

# HPCP computation
hpcp = es.HPCP(size=36)
hpcp_frames = []

for freq, conf in zip(pitch_values, pitch_confidence):
    if freq > 0:
        hpcp_frame = hpcp(essentia.array([freq]), essentia.array([conf]))
        hpcp_frames.append(hpcp_frame)
    else:
        hpcp_frames.append(essentia.array([0.0] * 36))  # Silence

# Chord detection
chord_detector = es.ChordsDetection()
chord_labels = []

for hpcp_frame in hpcp_frames:
    chord_label = chord_detector([hpcp_frame])[0][0]
    chord_labels.append(chord_label)

# Group by time
timeline = []
last_chord = None
start_frame = 0

for i, chord in enumerate(chord_labels):
    if chord != last_chord:
        if last_chord is not None:
            start_time = round((start_frame * hop_size) / sample_rate, 2)
            end_time = round((i * hop_size) / sample_rate, 2)
            duration = end_time - start_time
            if duration > 0.2:
                timeline.append((start_time, end_time, last_chord))
        last_chord = chord
        start_frame = i

# Final segment
end_time = round((len(chord_labels) * hop_size) / sample_rate, 2)
start_time = round((start_frame * hop_size) / sample_rate, 2)
duration = end_time - start_time
if duration > 0.2:
    timeline.append((start_time, end_time, last_chord))

# === STEP 5: SAVE TO FILES ===

# Print result
print("🎵 Detected Chords:")
for start, end, chord in timeline:
    print(f"{start:6.2f}s → {end:6.2f}s : {chord}")

# Save to CSV
output_csv = "detected_chords_clean.csv"
with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Start Time (s)", "End Time (s)", "Chord"])
    writer.writerows(timeline)
print("📁 Chords saved to", output_csv)

# Save to JSON (for Flutterflow or web use)
output_json = "detected_chords_clean.json"
with open(output_json, "w") as jf:
    json.dump([
        {"start": start, "end": end, "chord": chord}
        for start, end, chord in timeline
    ], jf, indent=2)
print("📁 Chords also saved to", output_json)

sys.exit(0)
