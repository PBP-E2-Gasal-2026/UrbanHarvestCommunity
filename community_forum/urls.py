from django.urls import path

from .views import show_community, create_post, create_comment

app_name = 'community_forum'

urlpatterns = [
    path('forum/', show_community, name='show_community'),
    path('forum/post/', create_post, name="create_post"),
    path("post/<uuid:post_id>/comment/", create_comment, name="create_comment"),
]
