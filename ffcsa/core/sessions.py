from django.contrib.sessions.backends.cached_db import SessionStore as CachedDBStore
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models
from mezzanine.conf import settings


class UserSession(AbstractBaseSession):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, db_index=True, on_delete=models.CASCADE)

    @classmethod
    def get_session_store_class(cls):
        return SessionStore


class SessionStore(CachedDBStore):
    cache_key_prefix = 'ffcsa_core.custom_cached_db_backend'

    @classmethod
    def get_model_class(cls):
        return UserSession

    def create_model_instance(self, data):
        obj = super(SessionStore, self).create_model_instance(data)
        try:
            user_id = int(data.get('_auth_user_id'))
        except (ValueError, TypeError):
            user_id = None
        obj.user_id = user_id
        return obj
