import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from local import get_application

application = get_application()
