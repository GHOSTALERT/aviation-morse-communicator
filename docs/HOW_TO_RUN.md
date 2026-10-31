# How to run

```bash
git clone https://github.com/GHOSTALERT/aviation-morse-communicator.git
cd aviation-morse-communicator
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

If new virtual environments have no `pip` (Debian/Ubuntu without `python3-venv`): `python3 -m venv --without-pip .venv && python3 -m pip --python .venv/bin/python install -r requirements.txt`.

## GUI

Needs Tk. On Debian/Ubuntu: `sudo apt install python3-tk`.

```bash
.venv/bin/python -m morse_app
```

## Command line

```bash
.venv/bin/python -m morse_app encode "MAYDAY MAYDAY MAYDAY" --wav mayday.wav --snr 0
.venv/bin/python -m morse_app decode "... --- ..."
.venv/bin/python -m morse_app decode-wav samples/mayday_snr0.wav
```

## Tests and the noise sweep

```bash
.venv/bin/python -m pytest -q tests          # 37 tests
.venv/bin/python scripts/snr_sweep.py         # results/snr_sweep.csv + figure
```

## Sound

On Windows the app uses `winsound`. On Linux or macOS install PyAudio:

```bash
sudo apt install portaudio19-dev && .venv/bin/pip install pyaudio
```

Without PyAudio the app runs silently, and the lamp and animation keep the same timing.

## Custom aircraft image

To use an aircraft image instead of the drawn silhouette, put `assets/airplane.png` in place; Pillow loads it.
