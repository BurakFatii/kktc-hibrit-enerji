import sys
from pathlib import Path

# Proje yalnızca kendi sanal ortamıyla (.venv, Python 3.13) çalışır. Sistemdeki başka bir `reflex`
# (ör. Homebrew Python 3.14) bağımlılıkları bulamaz ve çökerken .web/package.json'u bozar; bu yüzden erken dur.
_VENV = Path(__file__).resolve().parent / ".venv"
if Path(sys.prefix).resolve() != _VENV.resolve():
    sys.exit("\n[hibrit_enerji] Bu proje .venv içindeki reflex ile çalışır. Şunlardan birini kullanın:\n"
             "  source .venv/bin/activate && reflex run\n"
             "  .venv/bin/reflex run\n"
             f"(şu an kullanılan Python: {sys.executable})\n")

import reflex as rx  # noqa: E402
from reflex.plugins.sitemap import SitemapPlugin  # noqa: E402

config = rx.Config(
    app_name="hibrit_enerji",
    disable_plugins=[SitemapPlugin],  # Reflex 0.8.28 sınıf bekler (string verilirse DeprecationWarning)
)
