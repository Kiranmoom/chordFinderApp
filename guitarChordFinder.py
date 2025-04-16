import os
import subprocess
import tempfile
import csv
import requests
import essentia
import essentia.standard as es
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/detect-chords', methods=['POST'])
def detect_chords():
    data = request.get_json()
    if not data or 'audio_url' not in data:
        return jsonify({'error': 'No audio_url provided'}), 400

    audio_url = data['audio_url']
    print("Downloading audio file from:", audio_url)

    try:
        response = requests.get(audio_url)
        response.raise_for_status()
    except Exception as e:
        return jsonify({'error': f'Failed to download audio: {e}'}), 400

    # Create a temporary file (adjust the suffix if the file is m4a or mp3)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(response.content)
        tmp.flush()
        input_audio = tmp.name

    output_folder = "demucs_output"
    os.makedirs(output_folder, exist_ok=True)

    print("Running Demucs to isolate guitar...")
    command = [
        "demucs",
        "-n", "htdemucs_6s",
        "--two-stems", "guitar",
        input_audio,
        "--out", output_folder
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Demucs failed: {e}'}), 500

    # Build isolated guitar path
    base = os.path.splitext(os.path.basename(input_audio))[0]
    guitar_path = os.path.join(output_folder, "htdemucs_6s", base, "guitar.wav")
    if not os.path.exists(guitar_path):
        return jsonify({'error': 'Guitar stem not found.'}), 400

    print("Guitar-only audio ready:", guitar_path)

    # === Chord Detection ===
    print("Running chord detection on isolated guitar audio...")
    audio_data = es.MonoLoader(filename=guitar_path)()
    sample_rate = 44100
    frame_size = 2048
    hop_size = 128

    # Pitch tracking
    pitch_values, pitch_confidence = es.PredominantPitchMelodia(
        frameSize=frame_size,
        hopSize=hop_size
    )(audio_data)

    # HPCP computation
    hpcp = es.HPCP(size=36)
    hpcp_frames = [
        hpcp(essentia.array([f]), essentia.array([c])) if f > 0 else essentia.array([0.0] * 36)
        for f, c in zip(pitch_values, pitch_confidence)
    ]

    # Chord detection
    chord_detector = es.ChordsDetection()
    chord_labels = [chord_detector([frame])[0][0] for frame in hpcp_frames]

    # Group chords by time
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

    end_time = round((len(chord_labels) * hop_size) / sample_rate, 2)
    start_time = round((start_frame * hop_size) / sample_rate, 2)
    if (end_time - start_time) > 0.2:
        timeline.append((start_time, end_time, last_chord))

    os.remove(input_audio)

    chords_list = [{'start': s, 'end': e, 'chord': c} for s, e, c in timeline]
    return jsonify({'chords': chords_list}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Get Render's port if available
    try:
        app.run(debug=False, host='0.0.0.0', port=port)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Port {port} is already in use.")
        else:
            raise