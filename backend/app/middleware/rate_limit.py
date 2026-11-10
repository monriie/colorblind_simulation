"""slowapi rate limiter instance.

Uses client IP as the default key. Attach to specific routes
in the api/ routers via the ``@limiter.limit()`` decorator.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
