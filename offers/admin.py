from django.contrib import admin
from .models import Offre, Category, Images

admin.site.register(Category)
admin.site.register(Offre)
admin.site.register(Images)