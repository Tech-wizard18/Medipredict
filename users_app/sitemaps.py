from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class UsersSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return [
            'login',
            'register',
        ]

    def location(self, item):
        return reverse(item)
