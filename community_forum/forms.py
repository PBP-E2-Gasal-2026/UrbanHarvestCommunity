from django.forms import ModelForm, TextInput, Textarea

from .models import Post, Comment

class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = [
            "title",
            "content",
        ]
        labels = {
            "content": "Isi Postingan",
        }
        widgets = {
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
        fields = [
            "content",
        ]
        labels = {
            "content": "Isi komentar"
        }
        widgets = {
            "content": Textarea(
                attrs={
                    "placeholder": "Tuliskan komentar",
                    "rows": 3,
                }
            )
        }
