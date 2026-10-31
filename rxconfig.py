import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="hibrit_enerji",
    disable_plugins=[SitemapPlugin],
)
