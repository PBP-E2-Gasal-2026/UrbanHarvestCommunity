from .cart import cart_count


def cart(request):
    return {'cart_count': cart_count(request.user)}
