from cartridge.shop.managers import CartManager
from django.utils.timezone import now


class PersistentCartManager(CartManager):
    def from_request(self, request):
        """
        Return a cart by user ID from the authenticated user, updating its last_updated
        value and removing old carts. A new cart will be created (but not
        persisted in the database) if the session cart is expired or missing.
        """
        user_id = request.user.id
        cart_query = self.current().filter(user_id=user_id)
        cart_id = request.session.get("cart", None)

        last_updated = now()
        cart = cart_query.first()

        # Update timestamp and clear out old carts and put the cart_id in the session
        if cart and cart_query.update(last_updated=last_updated):
            self.expired().delete()
            cart_id = cart.id
            request.session["cart"] = cart_id
        elif cart_id:
            # Cart has expired. Delete the cart id and
            # forget what checkout step we were up to.
            del request.session["cart"]
            cart_id = None
            cart = None
            try:
                del request.session["order"]["step"]
            except KeyError:
                pass

        if cart:
            return cart
        else:
            return self.model(id=cart_id, last_updated=last_updated, user_id=user_id)
