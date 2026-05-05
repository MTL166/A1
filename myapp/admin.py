from django.contrib import admin
from myapp.models import Us
# Register your models here.

@admin.register(Us)
class UsAdmin(admin.ModelAdmin):
    list_display = ('id','name','password')
    list_display_links = ('name',)
    ordering = ('id',)