from django.urls import path

from .views import (
    login_view,
    logout_view,
    merchant_edit_view,
    profile_edit_view,
    profile_view,
    register_view,
    seller_application_list_view,
    seller_application_review_view,
    seller_apply_view,
)

app_name = 'authentication'

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),
    path('profile/<str:username>/', profile_view, name='profile'),
    path('seller/apply/', seller_apply_view, name='seller_apply'),
    path('seller/applications/', seller_application_list_view, name='seller_applications'),
    path('seller/applications/<int:pk>/review/', seller_application_review_view,
        name='seller_application_review'),
    path('merchant/edit/', merchant_edit_view, name='merchant_edit'),
]
