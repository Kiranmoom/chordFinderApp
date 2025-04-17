import os
import subprocess
import tempfile
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

    # 1) Download remote file
    try:
        resp = requests.get(audio_url)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({'error': f'Failed to download audio: {e}'}), 400

    # 2) Save to a temp file (m4a/mp3)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(resp.content)
        tmp.flush()
        m4a_path = tmp.name

    # 3) Convert to WAV via ffmpeg
    wav_path = m4a_path.replace(".m4a", ".wav")
    try:
        ffmpeg_result = subprocess.run(
            ["ffmpeg", "-y", "-i", m4a_path, "-ar", "44100", "-ac", "2", wav_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("FFmpeg conversion successful")
    except subprocess.CalledProcessError as e:
        print("FFmpeg stdout:", e.stdout)
        print("FFmpeg stderr:", e.stderr)
        return jsonify({'error': f'FFmpeg conversion failed: {e.stderr}'}), 500

    # 4) Prepare output folder
    output_folder = "demucs_output"
    os.makedirs(output_folder, exist_ok=True)

    # 5) Run Demucs
    print("Running Demucs to isolate guitar...")
    demucs_cmd = [
        "demucs",
        "-n", "htdemucs_6s",
        "--two-stems", "guitar",
        "--segment", "5",
        "-d", "cpu",
        wav_path,
        "--out", output_folder
    ]
    try:
        dem = subprocess.run(
            demucs_cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print("Demucs stdout:", dem.stdout)
        print("Demucs stderr:", dem.stderr)
    except subprocess.CalledProcessError as e:
        print("Demucs stdout (error):", e.stdout)
        print("Demucs stderr (error):", e.stderr)
        return jsonify({'error': f'Demucs crashed: {str(e)}'}), 500

    # 6) Find the guitar.wav output
    base = os.path.splitext(os.path.basename(wav_path))[0]
    guitar_path = os.path.join(output_folder, "htdemucs_6s", base, "guitar.wav")
    if not os.path.exists(guitar_path):
        return jsonify({'error': 'Guitar stem not found.'}), 500

    print("Guitar-only audio ready:", guitar_path)

    # === Chord Detection ===
    print("Running chord detection...")
    audio_data = es.MonoLoader(filename=guitar_path)()
    sample_rate = 44100
    frame_size = 2048
    hop_size = 128

    # Pitch tracking
    pitch_values, pitch_confidence = es.PredominantPitchMelodia(
        frameSize=frame_size,
        hopSize=hop_size
    )(audio_data)

    # HPCP and chord detection
    hpcp = es.HPCP(size=36)
    chord_detector = es.ChordsDetection()
    timeline = []

    last_chord = None
    start_frame = 0

    for i, (freq, conf) in enumerate(zip(pitch_values, pitch_confidence)):
        if freq > 0:
            hpcp_frame = hpcp(essentia.array([freq]), essentia.array([conf]))
            chord = chord_detector([hpcp_frame])[0][0]
        else:
            chord = "N"  # No chord

        if chord != last_chord:
            if last_chord is not None and last_chord != "N":
                start_time = round((start_frame * hop_size) / sample_rate, 2)
                end_time = round((i * hop_size) / sample_rate, 2)
                if end_time - start_time > 0.2:
                    timeline.append((start_time, end_time, last_chord))
            last_chord = chord
            start_frame = i

    # Final span
    end_time = round((len(pitch_values) * hop_size) / sample_rate, 2)
    start_time = round((start_frame * hop_size) / sample_rate, 2)
    if last_chord and last_chord != "N" and end_time - start_time > 0.2:
        timeline.append((start_time, end_time, last_chord))

    # 7) Cleanup temp files
    os.remove(m4a_path)
    os.remove(wav_path)

    chords_list = [{'start': s, 'end': e, 'chord': c} for s, e, c in timeline]
    return jsonify({'chords': chords_list}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
