# Compatibility shim — re-exports all model classes from domain modules.
# New code should import from the specific domain module instead.

from .users import *  # noqa: F401,F403
from .organizations import *  # noqa: F401,F403
from .creators import *  # noqa: F401,F403
from .catalog import *  # noqa: F401,F403
from .works import *  # noqa: F401,F403
from .releases import *  # noqa: F401,F403
from .contracts import *  # noqa: F401,F403
from .royalties import *  # noqa: F401,F403
from .financials import *  # noqa: F401,F403
from .analytics import *  # noqa: F401,F403
from .integrations import *  # noqa: F401,F403
from .notifications import *  # noqa: F401,F403
from .sharing import *  # noqa: F401,F403
from .misc import *  # noqa: F401,F403
