from django.contrib import admin
from .models import UserProfile, Connector, CleanupTask, CleanupExecution

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


@admin.register(CleanupTask)
class CleanupTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'table_name', 'is_active', 'retention_display', 'last_cleanup_at', 'created_at')
    list_filter = ('is_active', 'cleanup_frequency', 'created_at')
    search_fields = ('name', 'user__username', 'table_name')
    ordering = ('-created_at',)


@admin.register(CleanupExecution)
class CleanupExecutionAdmin(admin.ModelAdmin):
    list_display = ('cleanup_task', 'status', 'rows_deleted', 'started_at', 'duration')
    list_filter = ('status', 'started_at')
    search_fields = ('cleanup_task__name',)
    ordering = ('-started_at',)
