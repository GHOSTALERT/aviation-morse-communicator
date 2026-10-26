"""Signal synthesis, recognition from audio, WAV I/O and threaded playback."""
import threading
import time

import numpy as np
import pytest

from morse_app import audio, dsp
from morse_app import morse as m

MESSAGES = ["SOS", "MAYDAY MAYDAY MAYDAY", "HELLO WORLD", "CQ DE VTZ 123"]


@pytest.mark.parametrize("text", MESSAGES)
def test_clean_audio_round_trip(text):
    x = dsp.synthesize(m.encode_to_morse(text))
    a = dsp.analyse(x)
    assert a.text == text
    assert a.tone_hz == pytest.approx(700, abs=5)
    assert a.unit_s == pytest.approx(0.15, abs=0.02)


@pytest.mark.parametrize("text", MESSAGES)
@pytest.mark.parametrize("seed", range(3))
def test_noisy_audio_minus_5db(text, seed):
    x = dsp.synthesize(m.encode_to_morse(text), snr_db=-5, seed=seed)
    assert dsp.decode_audio(x) == text


def test_synth_length_matches_timing():
    code = m.encode_to_morse("SOS")
    x = dsp.synthesize(code, lead_s=0)
    assert x.size / dsp.FS * 1000 == pytest.approx(m.duration_ms(code), abs=2)


def test_other_tone_and_speed():
    # 1 kHz tone at 22.05 kHz sampling: tone frequency comes from the spectrum
    code = m.encode_to_morse("VOR")
    x = dsp.synthesize(code, fs=22050, freq=1000)
    a = dsp.analyse(x, 22050)
    assert a.text == "VOR"
    assert a.tone_hz == pytest.approx(1000, abs=10)


def test_wav_round_trip(tmp_path):
    path = tmp_path / "sos.wav"
    dsp.write_wav(path, dsp.synthesize(m.encode_to_morse("SOS"), snr_db=0))
    x, fs = dsp.read_wav(path)
    assert fs == dsp.FS
    assert dsp.decode_audio(x, fs) == "SOS"


def test_char_error_rate():
    assert dsp.char_error_rate("SOS", "SOS") == 0
    assert dsp.char_error_rate("SOS", "S?S") == pytest.approx(1 / 3)


def test_sine_tone_shape():
    t = audio.sine_tone(700, 150)
    assert t.dtype == np.float32
    assert t.size == int(audio.SAMPLE_RATE * 0.15)
    assert np.max(np.abs(t)) <= 0.3 + 1e-6
    assert abs(t[0]) < 1e-3 and abs(t[-1]) < 1e-2   # ramped edges, no click


class FakeRoot:
    """Stands in for tk.Tk: records after(0, cb) calls from the worker thread."""

    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()

    def after(self, _ms, cb, *args):
        with self.lock:
            self.calls.append(cb.__name__)
        cb(*args)


def test_threaded_playback_light_sync(monkeypatch):
    monkeypatch.setattr(audio, "WINSOUND_AVAILABLE", False)
    monkeypatch.setattr(audio, "PYAUDIO_AVAILABLE", False)
    monkeypatch.setattr(audio.time, "sleep", lambda s: None)   # run instantly
    root = FakeRoot()
    done = threading.Event()

    def light_on():
        pass

    def light_off():
        pass

    t = audio.play_morse_sound_threaded(root, "... ---", light_on, light_off, done.set)
    assert t.daemon
    t.join(timeout=5)
    assert done.is_set()
    # 6 elements: on/off for each, then a final off and done
    assert root.calls[:12] == ["light_on", "light_off"] * 6
    assert root.calls[12:] == ["light_off", "set"]


def test_threaded_playback_can_stop(monkeypatch):
    monkeypatch.setattr(audio, "WINSOUND_AVAILABLE", False)
    monkeypatch.setattr(audio, "PYAUDIO_AVAILABLE", False)
    stop = threading.Event()
    stop.set()
    root = FakeRoot()
    start = time.perf_counter()
    audio.play_morse_sound_threaded(root, "-----" * 10, lambda: None, lambda: None, None, stop).join(5)
    assert time.perf_counter() - start < 0.5
