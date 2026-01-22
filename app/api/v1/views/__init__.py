"""Views API submodule.

Expose a top-level `router` so that `app.api.v1` can include the views router.
"""

from .refresh import router

__all__ = ["router"]
