from django.contrib.sitemaps import Sitemap
from .models import Car, Category

class CarSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8
    
    def items(self):
        return Car.objects.all()
    
    def lastmod(self, obj):
        return obj.updated_at

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    
    def items(self):
        return Category.objects.all()
    
    def lastmod(self, obj):
        return obj.created_at