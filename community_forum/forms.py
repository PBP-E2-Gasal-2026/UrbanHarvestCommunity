from typing import ClassVar

from django.forms import ModelForm, Textarea

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields: ClassVar[list[str]] = [
            "content",
        ]
        labels: ClassVar[dict[str, str]] = {
            "content": "Isi Postingan",
        }
        widgets: ClassVar[dict[str, Textarea]] = {
            "content": Textarea(
                attrs={
                    "placeholder": "Apa yang ingin dibagikan?",
                    "rows": 6,
                }
            ),
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields: ClassVar[list[str]] = [
            "content",
        ]
        labels: ClassVar[dict[str, str]] = {
            "content": "Isi komentar"
        }
        widgets: ClassVar[dict[str, Textarea]] = {
            "content": Textarea(
                attrs={
                    "placeholder": "Tuliskan komentar",
                    "rows": 3,
                }
            )
        }
