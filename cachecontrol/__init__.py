"""CacheControl import Interface.

Make it easy to import from cachecontrol without long namespaces.
"""

# patch our requests.models.Response to make them pickleable in older
# versions of requests.

from . import patch_requests

from .wrapper import CacheControl
from .adapter import CacheControlAdapter
from .controller import CacheController
