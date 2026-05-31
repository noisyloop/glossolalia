import os
import sys

# Keep the suite fast and silent: no real sleeps, no audio backend, no
# visible tone fallbacks during assertions.
os.environ.setdefault("GLO_NO_AUDIO", "1")
os.environ.setdefault("GLO_TIME_SCALE", "0")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
