"""
Constants for ASL Weather Announce.

This module defines default paths and configuration values used throughout
the asl_weather application. These constants can be overridden via environment
variables or command-line arguments.
"""
import os

#: Default configuration file path. This is a system-wide config file
#: that contains weather announcement settings.
DEFAULT_CONFIG_PATH: str = os.environ.get("ASL_WEATHER_CONFIG", "/etc/asl_weather.conf")

#: Default directory containing voice files for text-to-speech.
#: Piper TTS voice models are stored here. This is a hardcoded path
#: and should not be overridden via environment variables, since
#: this is where asl-tts expects it to be.
DEFAULT_VOICE_DIR: str = "/var/lib/piper-tts"

#: NOTE: NOT USED, just in here for posterity.
#: Default log file path. The directory should be created by the
#: package installer with proper permissions (775, group asterisk).
#: Falls back to console logging if the file is not writable.
DEFAULT_LOG_FILE: str = os.environ.get("ASL_WEATHER_LOG_FILE", "/var/log/asl_weather/asl_weather.log")

#: Log level for the application. Can be overridden via the
#: LOG_LEVEL environment variable. Valid values: DEBUG, INFO, WARNING, ERROR.
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

#: Default timeout for HTTP requests in seconds.
DEFAULT_TIMEOUT: float = float(os.environ.get("ASL_WEATHER_TIMEOUT", "10.0"))

#: Default "true" words for the configuration file parser.
TRUE_WORDS: frozenset[str] = frozenset({
    "true",
    "t",
    "1",
    "one",
    "yes",
    "y",
    "ye",
    "yeah",
    "yep",
    "yup",
    "yas",
    "ok",
    "okay",
    "okey",
    "okk",
    "okey dokey",
    "okeydokey",
    "k",
    "for sure",
    "forsure",
    "sure",
    "for sizzle",
    "forsizzle",
    "certainly",
    "definitely",
    "absolutely",
    "indeed",
    "of course",
    "ofcourse",
    "on",
    "enable",
    "enabled",
    "active",
    "engage",
    "engaged",
    "affirmative",
    "roger",
    "copy",
    "copy that",
    "copythat",
    "that's a copy",
    "thatsacopy",
    "aye",
    "10-4",
    "10-04",
    "ten four",
    "tenfour",
    "alright",
    "all right",
    "fine",
    "good",
    "sounds good",
    "soundsgood",
    "sounds good to me",
    "soundsgoodtome",
    "works for me",
    "worksforme",
    "please",
    "yes please",
    "yesplease",
    "do it",
    "doit",
    "do that",
    "dothat",
    "go ahead",
    "goahead",
    "carry on",
    "carryon",
    "proceed",
    "why not",
    "whynot",
    "i agree",
    "iagree",
    "agreed",
    "i guess so",
    "iguessso",
    "guess so",
    "guessso",
    "correct",
    "right",
    "that is correct",
    "thatiscorrect",
    "uh huh",
    "uhhuh",
    "mm hmm",
    "mmhmm",
    "hell yeah",
    "hellyeah",
    "hell yea",
    "hells yea",
    "hellsyea",
    "hells yeah",
    "hellsyeah",
    "hellz yeah",
    "hellzyeah",
    "hellz yea",
    "hellzyea",
    "hellz yes",
    "hellzyes",
    "hell yes",
    "hellyes",
    "hells yes",
    "hellsyes",
})
