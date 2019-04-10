import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from local import get_application  # noqa

application = get_application()
