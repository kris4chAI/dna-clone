"""Where everything lives. One root (FLYHIGH_HOME) holds backend/, frontend/, skills/ and assets/.

Local checkout: the repository root. Docker image: /srv (same layout).
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.getenv("FLYHIGH_HOME", Path(__file__).resolve().parents[2]))
ASSETS = ROOT / "assets"
TEMPLATES = ASSETS / "templates"
SEED = ASSETS / "seed"
SKILLS = ROOT / "skills"
PURSUIT_SKILLS = SKILLS / "pursuit"
DELIVERY_SKILLS = SKILLS / "delivery"
PMO_SKILLS = SKILLS / "pmo"
PACKAGES = SKILLS / "packages"
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", ROOT / "frontend" / "dist"))

# the Snowflake skill generators are a package inside skills/delivery
if str(DELIVERY_SKILLS) not in sys.path:
    sys.path.insert(0, str(DELIVERY_SKILLS))
