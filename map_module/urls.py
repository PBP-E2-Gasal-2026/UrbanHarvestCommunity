from django.urls import path

from . import views

app_name = 'map_module'

urlpatterns = [
    path('', views.map_page, name='map'),
    path('mine/', views.my_locations, name='my_locations'),
    path('locations/new/', views.location_create, name='location_create'),
    path('locations/<int:pk>/', views.location_detail, name='location_detail'),
    path('locations/<int:pk>/edit/', views.location_update, name='location_update'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),
    path('api/locations/', views.api_locations, name='api_locations'),
    path('api/nearby/', views.api_nearby, name='api_nearby'),
]
