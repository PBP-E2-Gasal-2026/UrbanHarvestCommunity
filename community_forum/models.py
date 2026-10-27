import uuid
from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.

def validate_max_words(value, max_words=1000):
    if len(value.split()) > max_words:
        raise ValidationError(f"Maksimal {max_words} kata.")

class Post(models.Model):
    id_post = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey('User', on_delete=models.CASCADE)
    content = models.TextField(validators=[validate_max_words]) #Isi 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManytoManyField(
        'User',
        related_name="liked_posts",
        blank=True,
    )

    def __str__(self):
        return self.title

    @property
    def total_likes(self):
        return self.likes.count()

    @property
    def total_comments(self):
        return self.comments.count()
    
    class Meta:
        ordering = ["-created_at"]
    

class Comment(models.Model):
    id_comment = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name= "comments",)
    creator = models.ForeignKey('User', on_delete=models.CASCADE)
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["created_at"]