from django.contrib.auth import logout
from django.utils import timezone

from .models import Session


class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            active = Session.objects.filter(
                user=request.user,
                session_token=request.session.session_key,
                expires_at__gt=timezone.now(),
            ).exists()
            if not active:
                logout(request)
        return self.get_response(request)
