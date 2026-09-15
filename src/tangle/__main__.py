"""Enable ``python -m tangle`` to run the unified ``tangle`` command."""

from __future__ import annotations

from .main import main

raise SystemExit(main())
