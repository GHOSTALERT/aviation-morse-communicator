"""Cross-platform tone output.

Order of preference: winsound (Windows), PyAudio (any OS with PortAudio),
then silent timing with time.sleep so playback and the light stay in sync.
"""
import threading
import time

import numpy as np

from . import morse as m

try:
    import winsound
    WINSOUND_AVAILABLE = True
except Exception:
    WINSOUND_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except Exception:
    PYAUDIO_AVAILABLE = False

SAMPLE_RATE = 44100  # CD quality


def backend() -> str:
    if WINSOUND_AVAILABLE:
        return "winsound"
    if PYAUDIO_AVAILABLE:
        return "pyaudio"
    return "silent"


def sine_tone(frequency: float, duration_ms: float, amplitude: float = 0.3,
              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Sine tone with 5 ms raised-cosine edges, so it does not click."""
    frames = int(sample_rate * duration_ms / 1000.0)
    t = np.arange(frames) / sample_rate
    signal = np.sin(2 * np.pi * frequency * t) * amplitude
    ramp = min(int(0.005 * sample_rate), frames // 2)
    if ramp:
        edge = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, ramp))
        signal[:ramp] *= edge
        signal[-ramp:] *= edge[::-1]
    return signal.astype(np.float32)


def play_tone_pyaudio(frequency: float, duration_ms: float) -> None:
    """Generate and play a sine tone through PortAudio."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=SAMPLE_RATE, output=True)
    stream.write(sine_tone(frequency, duration_ms).tobytes())
    stream.stop_stream()
    stream.close()
    p.terminate()


def play_tone(frequency: float, duration_ms: float) -> None:
    """Blocking tone on whatever backend is available."""
    if WINSOUND_AVAILABLE:
        winsound.Beep(int(frequency), int(duration_ms))
    elif PYAUDIO_AVAILABLE:
        play_tone_pyaudio(frequency, duration_ms)
    else:
        time.sleep(duration_ms / 1000.0)


def play_morse(morse_code: str) -> None:
    """Blocking playback, for the command line."""
    for symbol in morse_code:
        if symbol in '.-':
            play_tone(m.TONE_FREQ, m.DOT_DURATION if symbol == '.' else m.DASH_DURATION)
            time.sleep(m.INTRA_ELEMENT_GAP / 1000.0)
        elif symbol == ' ':
            time.sleep(m.INTER_LETTER_GAP / 1000.0)
        elif symbol == '/':
            time.sleep(m.INTER_WORD_GAP / 1000.0)


def play_morse_sound_threaded(root, morse_code, light_on_callback, light_off_callback,
                              done_callback=None, stop_event=None):
    """Play Morse on a daemon thread and flash the light in step with it.

    GUI callbacks are handed to the Tk main loop with root.after(0, ...),
    because Tkinter widgets may only be touched from the main thread.
    """
    def worker():
        for symbol in morse_code:
            if stop_event is not None and stop_event.is_set():
                break
            if symbol in '.-':
                tone = m.DOT_DURATION if symbol == '.' else m.DASH_DURATION
                root.after(0, light_on_callback)
                play_tone(m.TONE_FREQ, tone)
                root.after(0, light_off_callback)
                time.sleep(m.INTRA_ELEMENT_GAP / 1000.0)
            elif symbol == ' ':
                time.sleep(m.INTER_LETTER_GAP / 1000.0)
            elif symbol == '/':
                time.sleep(m.INTER_WORD_GAP / 1000.0)
        root.after(0, light_off_callback)
        if done_callback is not None:
            root.after(0, done_callback)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
