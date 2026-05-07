from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import CustomUser, Notification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'user_type',
        'kyc_status',
        'kyc_reject_count',
        'phone',
        'is_staff',
    )
    list_filter = ('user_type', 'kyc_status', 'kyc_reject_count', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'company_name')
    readonly_fields = (
        'kyc_submitted_at',
        'kyc_reviewed_at',
        'privacy_registration_consent_at',
        'privacy_kyc_consent_at',
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'username',
                    'email',
                    'password1',
                    'password2',
                    'user_type',
                    'phone',
                    'company_name',
                ),
            },
        ),
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            'Profil client',
            {
                'fields': (
                    'phone',
                    'address',
                    'user_type',
                    'company_name',
                    'profile_image',
                    'privacy_registration_consent_at',
                )
            },
        ),
        (
            'Vérification d’identité (KYC)',
            {
                'fields': (
                    'kyc_status',
                    'kyc_reject_count',
                    'kyc_rejection_reason',
                    'kyc_submitted_at',
                    'kyc_reviewed_at',
                    'privacy_kyc_consent_at',
                    'kyc_id_document',
                    'kyc_id_back_document',
                    'kyc_proof_of_address',
                    'kyc_rc_document',
                    'kyc_tax_document',
                    'kyc_company_proof_of_address',
                ),
                'description': 'Validez ou refusez après examen des pièces. En cas de refus, l’utilisateur peut renvoyer un dossier (illimité).',
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if change and 'kyc_status' in form.changed_data:
            if obj.kyc_status in (CustomUser.KYC_APPROVED, CustomUser.KYC_REJECTED):
                obj.kyc_reviewed_at = timezone.now()
            if obj.kyc_status == CustomUser.KYC_REJECTED:
                obj.kyc_reject_count = int(obj.kyc_reject_count or 0) + 1
        super().save_model(request, obj, form, change)
        if change and 'kyc_status' in form.changed_data:
            if obj.kyc_status == CustomUser.KYC_APPROVED:
                Notification.objects.create(
                    user=obj,
                    notification_type='system',
                    title='Identité validée',
                    message='Votre vérification KYC est approuvée. Vous pouvez désormais louer du matériel.',
                    link='/comptes/dashboard/',
                )
            elif obj.kyc_status == CustomUser.KYC_REJECTED:
                Notification.objects.create(
                    user=obj,
                    notification_type='system',
                    title='Dossier KYC à corriger',
                    message=(
                        obj.kyc_rejection_reason
                        or 'Votre dossier n’a pas été accepté. Consultez la page Vérification d’identité pour envoyer de nouvelles pièces.'
                    ),
                    link='/comptes/verification-identite/',
                )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
