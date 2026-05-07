from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPE_PARTICULIER = 'particulier'
    USER_TYPE_ENTREPRISE = 'entreprise'
    USER_TYPE_CHOICES = [
        (USER_TYPE_PARTICULIER, 'Particulier'),
        (USER_TYPE_ENTREPRISE, 'Entreprise'),
    ]

    KYC_NOT_SUBMITTED = 'not_submitted'
    KYC_PENDING_REVIEW = 'pending_review'
    KYC_APPROVED = 'approved'
    KYC_REJECTED = 'rejected'
    KYC_STATUS_CHOICES = [
        (KYC_NOT_SUBMITTED, 'Non soumis'),
        (KYC_PENDING_REVIEW, 'En attente de vérification'),
        (KYC_APPROVED, 'Validé'),
        (KYC_REJECTED, 'Refusé'),
    ]

    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # Consentements RGPD / données personnelles (horodatage = preuve)
    privacy_registration_consent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Consentement inscription',
        help_text='Acceptation du traitement des données lors de la création du compte.',
    )
    privacy_kyc_consent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Consentement envoi dossier KYC',
        help_text='Acceptation du traitement des pièces et données pour la vérification KYC.',
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default=USER_TYPE_PARTICULIER,
    )
    kyc_status = models.CharField(
        max_length=20,
        choices=KYC_STATUS_CHOICES,
        default=KYC_NOT_SUBMITTED,
    )
    kyc_rejection_reason = models.TextField(blank=True)
    # Comptabilise le nombre de refus successifs (admin) pour limiter les re-soumissions.
    kyc_reject_count = models.PositiveIntegerField(default=0)
    kyc_submitted_at = models.DateTimeField(null=True, blank=True)
    kyc_reviewed_at = models.DateTimeField(null=True, blank=True)

    kyc_id_document = models.FileField(
        upload_to='kyc/particulier/',
        blank=True,
        null=True,
        verbose_name='Pièce d’identité',
        help_text='Particulier : CNI (recto)',
    )
    kyc_id_back_document = models.FileField(
        upload_to='kyc/particulier/',
        blank=True,
        null=True,
        verbose_name='CNI (verso)',
        help_text='Particulier : CNI (verso)',
    )
    kyc_proof_of_address = models.FileField(
        upload_to='kyc/particulier/',
        blank=True,
        null=True,
        verbose_name='Justificatif de domicile',
        help_text='Particulier : justificatif de domicile',
    )
    kyc_rc_document = models.FileField(
        upload_to='kyc/entreprise/',
        blank=True,
        null=True,
        verbose_name='Registre de commerce (RC)',
        help_text='Entreprise : extrait RC / registre de commerce',
    )
    kyc_tax_document = models.FileField(
        upload_to='kyc/entreprise/',
        blank=True,
        null=True,
        verbose_name='NIF / identifiant fiscal',
        help_text='Entreprise : NIF / identifiant fiscal',
    )
    kyc_company_proof_of_address = models.FileField(
        upload_to='kyc/entreprise/',
        blank=True,
        null=True,
        verbose_name='Justificatif de domicile (siège)',
        help_text='Entreprise : justificatif de domicile du siège',
    )

    def __str__(self):
        return self.username

    def kyc_documents_complete(self):
        if self.user_type == self.USER_TYPE_PARTICULIER:
            return bool(
                self.kyc_id_document
                and self.kyc_id_back_document
                and self.kyc_proof_of_address
            )
        return bool(
            self.kyc_rc_document
            and self.kyc_tax_document
            and self.kyc_company_proof_of_address
        )

    def can_rent_equipment(self):
        return self.kyc_status == self.KYC_APPROVED

class Notification(models.Model):
    NOTIF_TYPES = [
        ('reservation', 'Réservation'),
        ('payment', 'Paiement'),
        ('cancellation', 'Annulation'),
        ('reminder', 'Rappel'),
        ('penalty', 'Pénalité'),
        ('system', 'Système'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='system')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
