"""Morse signal synthesis and recognition from audio (report section X).

Synthesis turns a Morse string into a 700 Hz on/off-keyed tone with the
app's timing. Recognition runs the pipeline from section X.A on a sampled
signal and classifies the result with the timing rules of section X.B:

    normalise -> pre-emphasis -> tone frequency from the spectrum peak
    -> short-time spectrum, energy in a narrow band around the tone
    -> threshold with hysteresis -> on/off run lengths
    -> dot/dash and gap classification -> text
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import morse as m

FS = 8000          # sample rate for synthesis and analysis (Hz)
FRAME_MS = 20      # STFT window
HOP_MS = 5         # STFT hop, i.e. timing resolution
BAND_HZ = 60       # half-width of the band summed around the tone
SMOOTH_MS = 30     # moving-average length applied to the band envelope

# Nominal decision points (seconds) between the timing classes of section X.B
TONE_SPLIT = 0.30          # dot 150 ms | dash 450 ms
GAP_SPLIT_LETTER = 0.25    # intra-element 100 ms | letter gap 400 ms
GAP_SPLIT_WORD = 0.85      # letter gap 400 ms | word gap 1300 ms


def synthesize(morse_code: str, fs: int = FS, freq: float = m.TONE_FREQ,
               snr_db: float | None = None, seed: int = 0,
               lead_s: float = 0.3) -> np.ndarray:
    """Keyed sine tone for a Morse string, optionally with white Gaussian noise.

    snr_db is the ratio of mean tone power (while keyed) to noise power over
    the full band 0..fs/2.
    """
    def silence(ms):
        return np.zeros(int(fs * ms / 1000.0))

    def tone(ms):
        n = int(fs * ms / 1000.0)
        t = np.arange(n) / fs
        x = np.sin(2 * np.pi * freq * t)
        ramp = int(0.004 * fs)
        edge = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, ramp))
        x[:ramp] *= edge
        x[-ramp:] *= edge[::-1]
        return x

    parts = [silence(lead_s * 1000)]
    for symbol in morse_code:
        if symbol == '.':
            parts += [tone(m.DOT_DURATION), silence(m.INTRA_ELEMENT_GAP)]
        elif symbol == '-':
            parts += [tone(m.DASH_DURATION), silence(m.INTRA_ELEMENT_GAP)]
        elif symbol == ' ':
            parts.append(silence(m.INTER_LETTER_GAP))
        elif symbol == '/':
            parts.append(silence(m.INTER_WORD_GAP))
    parts.append(silence(lead_s * 1000))
    x = np.concatenate(parts)

    if snr_db is not None:
        rng = np.random.default_rng(seed)
        signal_power = 0.5  # unit-amplitude sine
        noise_power = signal_power / (10 ** (snr_db / 10))
        x = x + rng.normal(0.0, np.sqrt(noise_power), x.size)
    return x.astype(np.float32)


@dataclass
class Analysis:
    morse: str
    text: str
    tone_hz: float
    times: np.ndarray        # frame centres (s)
    envelope: np.ndarray     # band energy per frame
    threshold: float
    keyed: np.ndarray        # bool per frame
    tones: list              # (start_s, duration_s, '.'/'-')
    unit_s: float


def stft_band_energy(x: np.ndarray, fs: int, tone_hz: float):
    """Energy in [tone_hz +- BAND_HZ] for each STFT frame."""
    n = int(fs * FRAME_MS / 1000)
    hop = int(fs * HOP_MS / 1000)
    if x.size < n:
        x = np.pad(x, (0, n - x.size))
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop]
    spec = np.abs(np.fft.rfft(frames * np.hanning(n), axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / fs)
    band = (freqs >= tone_hz - BAND_HZ) & (freqs <= tone_hz + BAND_HZ)
    energy = spec[:, band].sum(axis=1)
    times = (np.arange(energy.size) * hop + n / 2) / fs
    return times, energy, freqs, spec


def _runs(mask: np.ndarray):
    """(value, start_index, length) for each run of equal values."""
    edges = np.flatnonzero(np.diff(mask.astype(np.int8))) + 1
    starts = np.concatenate([[0], edges])
    lengths = np.diff(np.concatenate([starts, [mask.size]]))
    return [(bool(mask[s]), int(s), int(l)) for s, l in zip(starts, lengths)]


def analyse(x: np.ndarray, fs: int = FS, min_run_ms: float = 30.0) -> Analysis:
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    peak = np.max(np.abs(x))
    if peak > 0:
        x = x / peak                                   # normalisation
    x = np.append(x[0], x[1:] - 0.97 * x[:-1])         # pre-emphasis

    spectrum = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(x.size, 1 / fs)
    search = (freqs > 200) & (freqs < 3000)
    tone_hz = float(freqs[search][np.argmax(spectrum[search])])

    times, energy, _, _ = stft_band_energy(x, fs, tone_hz)
    # Envelope, smoothed over SMOOTH_MS to steady it against noise
    k = max(1, int(round(SMOOTH_MS / HOP_MS)))
    env = np.convolve(np.sqrt(energy), np.ones(k) / k, mode='same')
    lo, hi = np.percentile(env, 20), np.percentile(env, 99)
    threshold = lo + 0.5 * (hi - lo)
    # Hysteresis: switch on above threshold, off below 70 % of it
    keyed = np.zeros(env.size, dtype=bool)
    state = False
    for i, v in enumerate(env):
        state = v > threshold if not state else v > 0.7 * threshold
        keyed[i] = state

    # Debounce: drop on/off runs shorter than min_run_ms
    hop_s = HOP_MS / 1000.0
    min_frames = max(1, int(round(min_run_ms / HOP_MS)))
    for value, start, length in _runs(keyed):
        if length < min_frames:
            keyed[start:start + length] = not value

    runs = _runs(keyed)
    # Trim leading/trailing silence
    while runs and not runs[0][0]:
        runs.pop(0)
    while runs and not runs[-1][0]:
        runs.pop()
    if not runs:
        return Analysis('', '', tone_hz, times, env, threshold, keyed, [], 0.0)

    on = np.array([l * hop_s for v, _, l in runs if v])
    scale = _speed_scale(on)
    unit = m.DOT_DURATION / 1000.0 * scale

    symbols, tones = [], []
    for value, start, length in runs:
        d = length * hop_s
        if value:
            s = '.' if d < TONE_SPLIT * scale else '-'
            symbols.append(s)
            tones.append((start * hop_s + times[0], d, s))
        elif d >= GAP_SPLIT_WORD * scale:
            symbols.append(' / ')
        elif d >= GAP_SPLIT_LETTER * scale:
            symbols.append(' ')
    morse_code = ' '.join(''.join(symbols).split())
    return Analysis(morse_code, m.decode_from_morse(morse_code), tone_hz,
                    times, env, threshold, keyed, tones, unit)


def _speed_scale(on_durations: np.ndarray) -> float:
    """Sending speed relative to the 150 ms dot.

    With both dots and dashes present the tone lengths form two clusters
    3:1 apart; the short cluster is the dot. With one class only, fall back
    to the nominal split.
    """
    d = np.sort(on_durations)
    if d.size >= 2:
        ratios = d[1:] / d[:-1]
        i = int(np.argmax(ratios))
        if ratios[i] > 2.0:
            return float(np.mean(d[:i + 1])) / (m.DOT_DURATION / 1000.0)
    return 1.0


def decode_audio(x: np.ndarray, fs: int = FS) -> str:
    return analyse(x, fs).text


def char_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein distance / reference length, on characters."""
    a, b = reference, hypothesis
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(1, len(a))


def write_wav(path, x: np.ndarray, fs: int = FS) -> None:
    """16-bit mono WAV with the standard-library wave module."""
    import wave
    pcm = np.clip(x / max(1e-9, np.max(np.abs(x))) * 0.9, -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes((pcm * 32767).astype('<i2').tobytes())


def read_wav(path):
    import wave
    with wave.open(str(path), 'rb') as w:
        fs = w.getframerate()
        ch = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    dtype = {1: np.uint8, 2: '<i2', 4: '<i4'}[width]
    x = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if width == 1:
        x -= 128
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, fs
