"""Platform selection. Windows stays on its separately validated v1 engine."""
import os

from .legacy_mlx_engine import LegacyMLXEngine  # historical v1 benchmark entry

if os.name == "nt":
    from .windows_engine import WindowsModelEngine as ModelEngine
else:
    from .mlx2_engine import MLX2Engine as ModelEngine
