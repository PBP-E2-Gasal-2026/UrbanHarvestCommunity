from django.urls import path

from .views import (
    create_comment,
    create_post,
    delete_comment,
    delete_post,
    edit_comment,
    edit_post,
    feed,
    show_community,
    toggle_like,
)

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
