import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from server import get_application  # noqa

application = get_application()
