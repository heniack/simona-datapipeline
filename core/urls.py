from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('connectors/', views.connector_list, name='connector_list'),
    path('connectors/google-drive/', views.google_drive_connectors, name='google_drive_connectors'),
    path('connectors/amazon-s3/', views.amazon_s3_connectors, name='amazon_s3_connectors'),
    path('connectors/create/', views.create_connector, name='create_connector'),
    path('connectors/<int:connector_id>/edit/', views.edit_connector, name='edit_connector'),
    path('connectors/<int:connector_id>/delete/', views.delete_connector, name='delete_connector'),
    path('connectors/<int:connector_id>/select-tables/', views.select_tables, name='select_tables'),
    path('connectors/<int:connector_id>/sync-now/', views.sync_connector_now, name='sync_connector_now'),
    path('connectors/<int:connector_id>/sync-tasks/', views.sync_task_list, name='sync_task_list'),
    path('connectors/<int:connector_id>/sync-tasks/create/', views.create_sync_task, name='create_sync_task'),
    path('sync-tasks/<int:sync_task_id>/execute/', views.execute_sync, name='execute_sync'),
    path('api/get-database-tables/', views.get_database_tables, name='get_database_tables'),
    path('google/authorize/', views.authorize_google_drive, name='authorize_google_drive'),
    path('oauth2callback', views.oauth2callback, name='oauth2callback'),
]
