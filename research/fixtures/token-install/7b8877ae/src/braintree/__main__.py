"""Enable ``python -m braintree`` to run the ``bt`` command."""

from __future__ import annotations

from .cli import main

raise SystemExit(main())
