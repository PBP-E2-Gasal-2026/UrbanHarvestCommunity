from django.contrib.auth import authenticate, login, logout
from django.contrib.sessions.models import Session as DjangoSession
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import RegistrationForm
from .models import Role, Session, User


def register_view(request):
    if request.user.is_authenticated:
        return redirect('main:show_main')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                )
                role, _ = Role.objects.get_or_create(
                    name='user', defaults={'description': 'Pengguna biasa'}
                )
                user.roles.add(role)
            return redirect('authentication:login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def _revoke_sessions(user):
    tokens = list(Session.objects.filter(user=user).values_list('session_token', flat=True))
    if tokens:
        DjangoSession.objects.filter(session_key__in=tokens).delete()
        Session.objects.filter(user=user).delete()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('main:show_main')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.roles.filter(name='user').exists():
            with transaction.atomic():
                User.objects.select_for_update().get(pk=user.pk)
                _revoke_sessions(user)
                login(request, user)
                request.session.save()
                Session.objects.create(
                    user=user,
                    session_token=request.session.session_key,
                    expires_at=request.session.get_expiry_date(),
                )
            return redirect('main:show_main')
        return render(request, 'login.html', {'error': 'Username atau password tidak valid.'})

    return render(request, 'login.html')


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            _revoke_sessions(request.user)
    logout(request)
    return redirect('authentication:login')
