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
    return render(request, "forum.html", {"posts": posts})


def show_community(request):
    posts = (Post.objects
            .select_related("creator")
            .prefetch_related("comments__user")
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
        return redirect("main:show_community")
        
    return render(request, "posts_form.html", {"form": form})


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
    else:
        messages.error(request, "Komentar tidak valid.")

    return redirect("main:show_community")



