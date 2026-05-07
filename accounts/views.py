from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .forms import CustomUserCreationForm, CustomAuthenticationForm, ProfileForm, KycDocumentForm
from .kyc import user_can_rent
from .models import CustomUser, Notification
from cart.models import Reservation

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.privacy_registration_consent_at = timezone.now()
            user.save(update_fields=['privacy_registration_consent_at'])
            login(request, user)
            Notification.objects.create(
                user=user,
                notification_type='system',
                title='Bienvenue sur RAOLY BTP !',
                message='Votre compte a été créé avec succès. Explorez notre catalogue de matériels de chantier.',
            )
            messages.success(
                request,
                'Compte créé ! Complétez ensuite la vérification d’identité (KYC) pour pouvoir louer du matériel.',
            )
            return redirect('accounts:kyc')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get('next', 'accounts:dashboard')
            return redirect(next_url)
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('core:home')

@login_required
def dashboard_view(request):
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    active_reservations = reservations.filter(status__in=['confirmed', 'active'])
    pending_reservations = reservations.filter(status='pending')
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:10]
    
    context = {
        'reservations': reservations[:10],
        'active_reservations': active_reservations,
        'pending_reservations': pending_reservations,
        'notifications': notifications,
        'total_reservations': reservations.count(),
    }
    return render(request, 'accounts/dashboard.html', context)

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)
    return render(request, 'accounts/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, pk):
    notif = Notification.objects.filter(pk=pk, user=request.user).first()
    if notif:
        notif.is_read = True
        notif.save()
    return redirect('accounts:notifications')

@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('accounts:notifications')

@login_required
def reservations_view(request):
    reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/reservations.html', {'reservations': reservations})


@login_required
def kyc_view(request):
    user = request.user
    if user_can_rent(user):
        messages.info(request, 'Votre identité est déjà validée. Vous pouvez louer du matériel.')
        return redirect('accounts:dashboard')

    # Verrouillage après 3 refus admin (resoumission non autorisée côté utilisateur).
    if user.kyc_status == CustomUser.KYC_REJECTED and user.kyc_reject_count >= 3:
        messages.error(
            request,
            'Nombre maximum de refus atteint (3). Contactez l’équipe RAOLY BTP pour réactiver votre dossier.',
        )
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        if user.kyc_status == CustomUser.KYC_PENDING_REVIEW:
            messages.info(request, 'Votre dossier est déjà en cours de vérification par un administrateur.')
            return redirect('accounts:kyc')
        if (
            user.user_type == CustomUser.USER_TYPE_ENTREPRISE
            and not (user.company_name or '').strip()
        ):
            messages.error(
                request,
                'Complétez la raison sociale dans Mon profil avant d’envoyer les pièces entreprise.',
            )
            return redirect('accounts:profile')
        form = KycDocumentForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            if user.kyc_documents_complete():
                user.kyc_status = CustomUser.KYC_PENDING_REVIEW
                user.kyc_submitted_at = timezone.now()
                user.kyc_rejection_reason = ''
                user.privacy_kyc_consent_at = timezone.now()
                user.save(
                    update_fields=[
                        'kyc_status',
                        'kyc_submitted_at',
                        'kyc_rejection_reason',
                        'privacy_kyc_consent_at',
                    ]
                )
                Notification.objects.create(
                    user=user,
                    notification_type='system',
                    title='Dossier KYC envoyé',
                    message=(
                        'Vos pièces ont été transmises. Un administrateur va vérifier votre dossier. '
                        'Vous recevrez une notification après validation.'
                    ),
                )
                messages.success(
                    request,
                    'Dossier envoyé. Vérification en cours par l’équipe RAOLY BTP.',
                )
                return redirect('accounts:kyc')
            messages.error(
                request,
                'Veuillez fournir tous les fichiers requis pour votre type de compte.',
            )
    else:
        form = KycDocumentForm(instance=user)

    return render(
        request,
        'accounts/kyc.html',
        {
            'form': form,
            'kyc_user': user,
        },
    )
