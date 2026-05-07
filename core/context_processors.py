from .models import SiteInfo

def site_info(request):
    info = SiteInfo.objects.first()
    cart_count = 0
    unread_notifications = 0
    if request.user.is_authenticated:
        from cart.models import CartItem
        cart_count = CartItem.objects.filter(user=request.user).count()
        from accounts.models import Notification
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'site_info': info,
        'cart_count': cart_count,
        'unread_notifications': unread_notifications,
    }
