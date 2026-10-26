from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session as DjangoSession
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LoginForm, ProfileForm, RegistrationForm, SellerReviewForm, MerchantForm
from .models import Profile, Role, Session, User, SellerApplication, Merchant
from .permissions import admin_required, has_role, role_required


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
                    name='farmer', defaults={'description': 'Petani'}
                )
                user.roles.add(role)
                Profile.objects.create(user=user) ############################################################
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
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
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
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            _revoke_sessions(request.user)
    logout(request)
    return redirect('authentication:login')

def profile_view(request, username) :
    profile_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=profile_user)
    merchant = None
    if has_role(profile_user, 'farmer-seller'):
        merchant = Merchant.objects.filter(owner=profile_user).first()
    return render(request, 'profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'merchant': merchant,
        'is_owner': request.user == profile_user,
    })

@login_required
def profile_edit_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('authentication:profile', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profile_edit.html', {'form': form})

@role_required('farmer')
def seller_apply_view(request):
    if request.method == 'POST':
        if has_role(request.user, 'farmer-seller'):
            messages.error(request, 'Kamu sudah menjadi penjual.')
        else:
            try:
                with transaction.atomic():
                    SellerApplication.objects.create(applicant=request.user)
            except IntegrityError:
                messages.error(request, 'Pengajuanmu masih menunggu tinjauan Admin.')
            else:
                messages.success(request, 'Pengajuan berhasil dikirim.')
        return redirect('authentication:seller_apply')

    return render(request, 'seller_apply.html', {
        'applications': request.user.seller_applications.all(),
        'is_seller': has_role(request.user, 'farmer-seller'),
    })

@role_required('farmer-seller')
def merchant_edit_view(request):
    merchant = Merchant.objects.filter(owner=request.user).first()
    if request.method == 'POST':
        form = MerchantForm(request.POST, instance=merchant)
        if form.is_valid():
            merchant = form.save(commit=False)
            merchant.owner = request.user
            merchant.save()
            messages.success(request, 'Profil merchant berhasil disimpan.')
            return redirect('authentication:profile', username=request.user.username)
    else:
        form = MerchantForm(instance=merchant)
    return render(request, 'merchant_edit.html', {
        'form': form,
        'is_new': merchant is None,
    })


@admin_required
def seller_application_list_view(request):
    applications = (
        SellerApplication.objects
        .filter(status=SellerApplication.Status.PENDING)
        .select_related('applicant')
        .order_by('created_at')
    )
    return render(request, 'seller_applications.html', {
        'applications': applications,
        'form': SellerReviewForm(),
    })


@admin_required
@require_POST
def seller_application_review_view(request, pk):
    form = SellerReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Keputusan tidak valid.')
        return redirect('authentication:seller_applications')

    with transaction.atomic():
        application = get_object_or_404(
            SellerApplication.objects.select_for_update(), pk=pk
        )
        if application.status != SellerApplication.Status.PENDING:
            messages.error(request, 'Pengajuan ini sudah ditinjau.')
            return redirect('authentication:seller_applications')

        application.status = form.cleaned_data['decision']
        application.admin_note = form.cleaned_data['admin_note']
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()

        if application.status == SellerApplication.Status.APPROVED:
            role, _ = Role.objects.get_or_create(
                name='farmer-seller', defaults={'description': 'Petani penjual'}
            )
            application.applicant.roles.add(role)

    messages.success(request, 'Pengajuan berhasil ditinjau.')
    return redirect('authentication:seller_applications')