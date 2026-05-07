"""Contrôle d'accès location selon le statut KYC."""


def user_can_rent(user):
    return user.is_authenticated and getattr(user, 'kyc_status', '') == 'approved'


def kyc_redirect_message():
    return (
        'Votre identité doit être vérifiée (KYC) avant de louer du matériel. '
        'Complétez et soumettez vos pièces depuis la page Vérification d’identité.'
    )
