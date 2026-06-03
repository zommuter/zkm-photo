"""zkm-photo — filesystem-discovery shim; delegates to the zkm_photo package.

Loaded by core when the plugin is filesystem-discovered (dev-symlink workflow).
Core's _inject_plugin_venv (SB2) adds plugins/zkm-photo/src/ to sys.path before
loading this file, making zkm_photo importable here.
"""

from zkm_photo.convert import convert  # noqa: F401
