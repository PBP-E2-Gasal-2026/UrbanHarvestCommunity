from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Comment, Post

FEED_ORDERING = {
    "terbaru": ("-created_at",),
    "populer": ("-like_count", "-comment_count", "-created_at"),
}


def feed(request):
    urut = request.GET.get("urut") if request.GET.get("urut") in FEED_ORDERING else "terbaru"
    posts = (
        Post.objects
        .select_related("creator")
        .prefetch_related("likes")
        .annotate(
            like_count=Count("likes", distinct=True),
            comment_count=Count("comments", distinct=True),
        )
        .order_by(*FEED_ORDERING[urut])
    )
    return render(request, "feed.html", {"post_list": posts, "urut": urut})


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
        "member_count": Post.objects.values("creator").distinct().count(),
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
        # Kotak tulis di feed mengirim next=/forum/feed/ agar pengguna kembali ke sana.
        next_url = request.POST.get("next", "")
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
            return redirect(next_url)
        return redirect(f"{reverse('community_forum:show_community')}#post-{post.pk}")

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
    liked = not post.likes.filter(pk=request.user.pk).exists()
    if liked:
        post.likes.add(request.user)
    else:
        post.likes.remove(request.user)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"liked": liked, "count": post.likes.count()})
    return redirect(f"{reverse('community_forum:show_community')}#post-{post.pk}")


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
        return redirect(f"{reverse('community_forum:show_community')}#post-{post.pk}")

    return render(request, "comments_form.html", {"form": form, "post": post, "is_edit": False})


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id, creator=request.user)
    form = CommentForm(request.POST or None, instance=comment)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Komentar berhasil diperbarui!")
        return redirect("community_forum:show_community")

    return render(
        request, "comments_form.html", {"form": form, "comment": comment, "post": comment.post, "is_edit": True}
    )

    
@login_required
@require_POST
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id, creator=request.user)
    comment.delete()
    messages.success(request, "Komentar berhasil dihapus!")
    return redirect("community_forum:show_community")

