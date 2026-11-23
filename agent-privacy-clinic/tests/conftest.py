import os
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..")
for p in (os.path.join(ROOT, "agent-action-record", "src"), os.path.join(ROOT, "agent-action-record"), os.path.join(HERE, "..")):
    sys.path.insert(0, os.path.abspath(p))
