from .models import Favorite

def favorites_info(request):
    if request.user.is_authenticated:
        count = Favorite.objects.filter(user=request.user).count()
        fav_ids = list(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    else:
        s_key = request.session.session_key
        count = Favorite.objects.filter(session_key=s_key).count() if s_key else 0
        fav_ids = list(Favorite.objects.filter(session_key=s_key).values_list('product_id', flat=True)) if s_key else []

    return {
        'fav_count': count,
        'fav_ids': fav_ids
    }