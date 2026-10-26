"""Command line entry point.

    python -m morse_app                       # GUI
    python -m morse_app encode "MAYDAY" [--wav out.wav] [--snr -5] [--play]
    python -m morse_app decode "-- .- -.-- -.. .- -.--"
    python -m morse_app decode-wav recording.wav
"""
import argparse
import sys

from . import audio, dsp
from . import morse as m


def main(argv=None):
    p = argparse.ArgumentParser(prog="morse_app", description="Aviation Morse Code Communicator")
    sub = p.add_subparsers(dest="cmd")

    enc = sub.add_parser("encode", help="text to Morse")
    enc.add_argument("text")
    enc.add_argument("--wav", help="also write the keyed tone to this WAV file")
    enc.add_argument("--snr", type=float, help="add white noise at this SNR (dB) to the WAV")
    enc.add_argument("--play", action="store_true", help="play through the audio backend")

    dec = sub.add_parser("decode", help="Morse to text")
    dec.add_argument("morse")

    dw = sub.add_parser("decode-wav", help="recognise Morse in a WAV recording")
    dw.add_argument("path")

    args = p.parse_args(argv)

    if args.cmd is None:
        from .app import main as gui
        gui()
    elif args.cmd == "encode":
        code = m.encode_to_morse(args.text)
        print(code)
        if args.wav:
            dsp.write_wav(args.wav, dsp.synthesize(code, snr_db=args.snr))
            print(f"wrote {args.wav} ({m.duration_ms(code) / 1000:.1f} s of Morse)", file=sys.stderr)
        if args.play:
            print(f"playing via {audio.backend()}", file=sys.stderr)
            audio.play_morse(code)
    elif args.cmd == "decode":
        print(m.decode_from_morse(args.morse))
    elif args.cmd == "decode-wav":
        x, fs = dsp.read_wav(args.path)
        a = dsp.analyse(x, fs)
        print(a.morse)
        print(a.text)
        print(f"tone {a.tone_hz:.0f} Hz, dot {a.unit_s * 1000:.0f} ms, {len(a.tones)} elements",
              file=sys.stderr)


if __name__ == "__main__":
    main()
