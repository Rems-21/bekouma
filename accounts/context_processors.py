from .kyc import user_can_rent


def kyc_rental_gate(request):
    if request.user.is_authenticated:
        return {
            'user_can_rent': user_can_rent(request.user),
            'user_kyc_status': getattr(request.user, 'kyc_status', ''),
        }
    return {'user_can_rent': False, 'user_kyc_status': ''}
