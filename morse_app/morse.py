"""International Morse code dictionary, encoder and decoder.

Text format used throughout the app: one space between letters, "/" between
words, e.g. "HELLO WORLD" -> ".... . .-.. .-.. --- / .-- --- .-. .-.. -..".
"""

MORSE_CODE_DICT = {
    'A': '.-',    'B': '-...',  'C': '-.-.',  'D': '-..',   'E': '.',
    'F': '..-.',  'G': '--.',   'H': '....',  'I': '..',    'J': '.---',
    'K': '-.-',   'L': '.-..',  'M': '--',    'N': '-.',    'O': '---',
    'P': '.--.',  'Q': '--.-',  'R': '.-.',   'S': '...',   'T': '-',
    'U': '..-',   'V': '...-',  'W': '.--',   'X': '-..-',  'Y': '-.--',
    'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
    '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
    ' ': '/',     # word separator
}

MORSE_TO_TEXT = {v: k for k, v in MORSE_CODE_DICT.items()}

# Standard timing (ms). Dash = 3 x dot.
DOT_DURATION = 150
DASH_DURATION = 450
INTRA_ELEMENT_GAP = 100
INTER_LETTER_GAP = 300
INTER_WORD_GAP = 600
TONE_FREQ = 700  # Hz

# Aviation presets used by the Application section
PRESETS = {
    "MAYDAY": "MAYDAY MAYDAY MAYDAY",
    "SOS": "SOS",
    "PAN-PAN": "PAN PAN PAN PAN PAN PAN",
    "VOR ident (VTZ)": "VTZ",
}


def encode_to_morse(text: str) -> str:
    """Convert text to Morse. Characters with no Morse equivalent are skipped."""
    words = text.upper().split()
    coded = []
    for word in words:
        letters = [MORSE_CODE_DICT[c] for c in word if c in MORSE_CODE_DICT]
        if letters:
            coded.append(' '.join(letters))
    return ' / '.join(coded)


def decode_from_morse(morse_code: str) -> str:
    """Convert Morse back to text. Unknown symbols decode to '?'."""
    words = morse_code.split('/')
    decoded_text = ''
    for word in words:
        for symbol in word.split():
            decoded_text += MORSE_TO_TEXT.get(symbol, '?')
        decoded_text += ' '
    return ' '.join(decoded_text.split())


def is_valid_morse(morse_code: str) -> bool:
    """True if the string only contains dots, dashes, spaces and slashes."""
    return bool(morse_code.strip()) and set(morse_code) <= set('.-/ ')


def duration_ms(morse_code: str) -> int:
    """Playback time of a Morse string with the standard timing above."""
    total = 0
    for symbol in morse_code:
        if symbol == '.':
            total += DOT_DURATION + INTRA_ELEMENT_GAP
        elif symbol == '-':
            total += DASH_DURATION + INTRA_ELEMENT_GAP
        elif symbol == ' ':
            total += INTER_LETTER_GAP
        elif symbol == '/':
            total += INTER_WORD_GAP
    return total
