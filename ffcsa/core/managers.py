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
        cart = self.current().filter(user_id=user_id)
        cart_id = request.session.get("cart", None)

        last_updated = now()

        # Update timestamp and clear out old carts and put the cart_id in the session
        if cart.first() and cart.update(last_updated=last_updated):
            self.expired().delete()
            cart_id = cart.first().id
            request.session["cart"] = cart_id
        elif cart_id:
            # Cart has expired. Delete the cart id and
            # forget what checkout step we were up to.
            del request.session["cart"]
            cart_id = None
            try:
                del request.session["order"]["step"]
            except KeyError:
                pass

        # This is a cheeky way to save a database call: since Cart only has
        # two fields and we know both of their values, we can simply create
        # a cart instance without taking a trip to the database via the ORM.
        return self.model(id=cart_id, last_updated=last_updated, user_id=user_id)
