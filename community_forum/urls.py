from django.urls import path

from .views import show_community, create_post, create_comment, edit_post, delete_post, toggle_like, edit_comment, delete_comment, feed

app_name = 'community_forum'

urlpatterns = [
    path('', show_community, name='show_community'),
    path('post/', create_post, name="create_post"),
    path("<uuid:post_id>/comment/", create_comment, name="create_comment"),
    path("<uuid:post_id>/edit/", edit_post, name="edit_post"),
    path("<uuid:post_id>/delete/", delete_post, name="delete_post"),
    path("<uuid:post_id>/like/", toggle_like, name="toggle_like"),
    path("<uuid:post_id>/<uuid:comment_id>/edit/", edit_comment, name="edit_comment"),
    path("<uuid:post_id>/<uuid:comment_id>/delete/", delete_comment, name="delete_comment"),
    path("feed/", feed, name="feed"),
]
