# Aviation Morse Code Communicator: Simulation-Based Training and Educational Software

Signal Processing course project, School of Electronics Engineering (SENSE), VIT Vellore. Team: Arrnav Trisal (24BVD0064), Aditya Manoj (24BVD0070), Gavin Shalan Fernandes (24BVD0083), Jyothiraditya (24BVD0205). Guide: Dr. Shweta B. Thomas.

A Python/Tkinter trainer for Morse code in aviation. It encodes and decodes text and plays a 700 Hz tone, with a signal lamp that flashes in step. It also animates an aircraft-to-ATC transmission with presets such as MAYDAY, SOS, PAN-PAN and VOR idents. Audio is cross-platform: `winsound` on Windows, PyAudio elsewhere, and silent timing if neither is available. Playback runs on a daemon thread, and all widget updates go through `root.after()`, so the GUI never freezes.

The submitted report is in [`report/Aviation_Morse_Code_Communicator_Report.pdf`](report/Aviation_Morse_Code_Communicator_Report.pdf).
This repo also implements the report's signal-processing section (X) in [`morse_app/dsp.py`](morse_app/dsp.py). It synthesises the keyed tone and recognises Morse from a WAV recording with a spectrogram band-energy detector and timing classification.

## Features

| Section | What it does |
|---|---|
| Learn Morse Code | Chart of A-Z and 0-9. Click any symbol to hear it and see the lamp |
| Encode Text | Text to Morse (letters separated by spaces, words by `/`), play it, save as WAV, copy. Characters with no Morse code are skipped and listed |
| Decode Morse | Morse to text (unknown symbols become `?`), or decode a WAV recording |
| Application | Three-phase animation: the aircraft approaches, transmits while the ATC panel shows the code and the lamp flashes, then departs. Presets: MAYDAY, SOS, PAN-PAN, VOR ident |

| Learn | Encode |
|---|---|
| ![Learn](docs/screenshots/learn.png) | ![Encode](docs/screenshots/encode.png) |
| **Decode** (here: a noisy WAV recording) | **Application** (transmitting, lamp lit) |
| ![Decode](docs/screenshots/decode.png) | ![Application](docs/screenshots/application.png) |

Timing, as in the report:

| Element | Duration |
|---|---|
| Dot | 150 ms |
| Dash | 450 ms (3 × dot) |
| Gap within a letter | 100 ms |
| Gap between letters | 300 ms |
| Gap between words | 600 ms |
| Tone | 700 Hz |

## Signal processing: recognising Morse from audio

`dsp.analyse()` steps:

1. Normalise and pre-emphasise (`y[n] = x[n] - 0.97 x[n-1]`).
2. Find the tone frequency from the spectrum peak (200-3000 Hz).
3. Short-time spectrum (20 ms Hann window, 5 ms hop). Take the energy in a ±60 Hz band around the tone and smooth it over 30 ms.
4. Threshold with hysteresis, then discard on/off runs shorter than 30 ms.
5. Estimate sending speed from the two tone-length clusters (dash ≈ 3 × dot).
6. Classify each run: dot or dash, then intra-letter, letter or word gap. Look up the text.

![Pipeline](results/figures/pipeline_mayday.png)

Accuracy against white noise ([`scripts/snr_sweep.py`](scripts/snr_sweep.py); 5 messages × 20 noise seeds per point; SNR measured over the full 0-4 kHz band):

| SNR (dB) | 10 to -6 | -7 | -8 | -9 | -10 | -12 |
|---|---|---|---|---|---|---|
| Messages decoded exactly | 100 % | 93 % | 75 % | 48 % | 20 % | 2 % |

## Run it

```bash
cd ~/Downloads/aviationMorseProj
python3 -m venv --without-pip .venv
python3 -m pip --python .venv/bin/python install -r requirements.txt

# GUI (needs Tk: on Debian/Ubuntu  sudo apt install python3-tk)
.venv/bin/python -m morse_app

# Command line
.venv/bin/python -m morse_app encode "MAYDAY MAYDAY MAYDAY" --wav mayday.wav --snr 0
.venv/bin/python -m morse_app decode "... --- ..."
.venv/bin/python -m morse_app decode-wav samples/mayday_snr0.wav

# Tests (report test cases, audio round trips, threading) and the noise sweep
.venv/bin/python -m pytest -q tests
.venv/bin/python scripts/snr_sweep.py
```

For sound on Linux or macOS, install PyAudio (`sudo apt install portaudio19-dev && pip install pyaudio`). Without it the app runs silently, and the lamp and animation keep the same timing.

To use an aircraft image instead of the drawn silhouette, put `assets/airplane.png` in place; Pillow loads it.

## Tests

`tests/test_morse.py` covers the report's test table: encoding MAYDAY, decoding SOS, skipping unknown characters (`A@B` encodes as `AB`), the word separator, and round trips. `tests/test_dsp_audio.py` checks clean and −5 dB audio decoding, other tones and sample rates, WAV I/O, and that the threaded player flashes the lamp on and off for each element through `root.after`. 37 tests pass.

## Layout

```
morse_app/   morse.py (dictionary, encode/decode, timing), audio.py (winsound/PyAudio/silent, threaded player),
             dsp.py (synthesis, recognition, WAV I/O), app.py (Tkinter GUI), __main__.py (CLI)
tests/       test_morse.py, test_dsp_audio.py
scripts/     snr_sweep.py
results/     snr_sweep.csv, figures/
samples/     sos_clean.wav, mayday_snr0.wav, vor_ident_vtz.wav
docs/        screenshots/ of the four GUI sections
report/      submitted report (PDF)
```
