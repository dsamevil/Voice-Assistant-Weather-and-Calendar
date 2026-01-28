import sounddevice as sd
import scipy.io.wavfile as wav
import pyttsx3
from faster_whisper import WhisperModel
import numpy as np
import os
import sys
import time  # Import time for the pause fix

# --- CONFIGURATION ---
print("Loading Whisper model... please wait.")
model = WhisperModel("base", device="cpu", compute_type="int8")

# --- FUNCTIONS ---

def speak_text(text):
    """
    Converts text to speech.
    Uses 'sapi5' driver (Windows standard) and re-initializes engine
    each time to prevent audio driver conflicts.
    """
    print(f"\nAssistant: {text}")
    
    # FIX 1: Tiny pause to let the microphone release the audio device
    time.sleep(0.5) 
    
    try:
        # FIX 2: Re-initialize engine locally for robustness
        engine = pyttsx3.init('sapi5') 
        engine.setProperty('volume', 1.0)
        engine.setProperty('rate', 170)
        
        engine.say(text)
        engine.runAndWait()
        
        # Cleanup (helps prevents errors on next loop)
        engine.stop()
        del engine
    except Exception as e:
        print(f"[Error] TTS failed: {e}")

def record_audio(filename="input.wav", silence_threshold=800, silence_duration=2.5, samplerate=16000):
    """
    Smart recording with Volume Meter.
    """
    print("\n[Microphone Active] Waiting for you to speak...")
    
    audio_data = []
    chunk_duration = 0.2 
    chunk_samples = int(chunk_duration * samplerate)
    
    has_started = False
    silence_chunks = 0
    max_silence_chunks = int(silence_duration / chunk_duration)
    
    # Open stream
    with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
        while True:
            chunk, overflow = stream.read(chunk_samples)
            
            # Use Peak Amplitude
            volume = np.max(np.abs(chunk))
            
            # Live volume meter
            bar_len = int(volume / 500) 
            bar = "#" * min(bar_len, 20)
            sys.stdout.write(f"\rVolume: {volume:5d} [{bar:<20}]")
            sys.stdout.flush()

            if not has_started:
                # WAITING MODE
                if volume > silence_threshold:
                    print("\n\n>>> Speech detected! Recording...")
                    has_started = True
                    audio_data.append(chunk)
            else:
                # RECORDING MODE
                audio_data.append(chunk)
                
                if volume < silence_threshold:
                    silence_chunks += 1
                else:
                    silence_chunks = 0 
                
                if silence_chunks > max_silence_chunks:
                    print("\nSilence detected. Stopping recording.")
                    break
    
    # End of recording loop
    if not audio_data:
        return None
        
    full_audio = np.concatenate(audio_data, axis=0)
    wav.write(filename, samplerate, full_audio)
    return filename

def transcribe_audio(filename="input.wav"):
    if not os.path.exists(filename):
        return ""
    
    try:
        segments, info = model.transcribe(filename, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        
        if text.strip():
            print(f"User said: {text}")
            return text.strip()
        else:
            return ""
    except Exception as e:
        print("Error during transcription:", e)
        return ""

if __name__ == "__main__":
    # Test block
    audio = record_audio()
    if audio:
        transcribe_audio(audio)