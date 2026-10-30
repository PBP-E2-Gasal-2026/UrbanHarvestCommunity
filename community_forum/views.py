from django.contrib import messages
from django.core import serializers
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comment
from .forms import PostForm, CommentForm

# Create your views here.
def feed(request):
    posts = (
        Post.objects
        .select_related("creator")
        .annotate(
            like_count=Count("likes", distinct=True),
            comment_count=Count("comments", distinct=True),
        )
        .order_by("-created_at")
    )
    return render(request, "feed.html", {"posts": posts})


def show_community(request):
    posts = (Post.objects
            .select_related("creator")
            .prefetch_related("comments__creator", "likes")
            .annotate(
                like_count=Count("likes", distinct=True),
                comment_count=Count("comments", distinct=True),
            )
            .order_by("-created_at")
    )

    context = {
        "post_list": posts,
        "comment_form": CommentForm(),
    }
    return render(request, "forum.html", context)


@login_required
def create_post(request):
    form = PostForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.creator = request.user
        post.save()
        messages.success(request, "Postingan baru berhasil ditambahkan!")
        return redirect("community_forum:show_community")
        
    return render(request, "posts_form.html", {"form": form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id, creator=request.user)
    form = PostForm(request.POST or None, instance=post)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Postingan berhasil diperbarui!")
        return redirect("community_forum:show_community")

    return render(request, "posts_form.html", {"form": form, "post": post})


@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id, creator=request.user)
    post.delete()
    messages.success(request, "Postingan berhasil dihapus!")
    return redirect("community_forum:show_community")


@login_required
@require_POST
def toggle_like(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect("community_forum:show_community")


@login_required
@require_POST
def create_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.creator = request.user
        comment.save()
        messages.success(request, "Komentar berhasil ditambahkan!")
        return redirect("community_forum:show_community")

    return render(request, "comments_form.html", {"form": form, "post": post})


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, creator=request.user)
    form = CommentForm(request.POST or None, instance=comment)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Komentar berhasil diperbarui!")
        return redirect("community_forum:show_community")

    return render(request, "comments_form.html", {"form": form, "comment": comment})

    
@login_required
@require_POST
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, creator=request.user)
    comment.delete()
    messages.success(request, "Komentar berhasil dihapus!")
    return redirect("community_forum:show_community")

