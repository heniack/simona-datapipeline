from django.contrib import admin
from .models import UserProfile, Connector

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-created_at',)

@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'destination_type', 'is_active', 'created_at')
    list_filter = ('destination_type', 'is_active', 'created_at')
    search_fields = ('name', 'user__username')
    ordering = ('-created_at',)
