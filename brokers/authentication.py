"""
DRF Authentication class for the Broker Portal.
Supports:
- Authorization: BrokerToken <session_token>
- Authorization: Bearer <session_token>  (frontend compatibility)
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import BrokerSession
import logging

logger = logging.getLogger(__name__)


class BrokerTokenAuthentication(BaseAuthentication):
    """Authenticate broker portal requests via BrokerSession token."""

    keyword = 'BrokerToken'

    def _extract_token(self, auth_header):
        if not auth_header:
            return None

        if auth_header.startswith(f'{self.keyword} '):
            token = auth_header[len(self.keyword) + 1:].strip()
            return token or None

        # Compatibility: allow Bearer broker-session tokens.
        # Ignore JWT-like Bearer tokens so they don't get treated as broker tokens.
        if auth_header.startswith('Bearer '):
            token = auth_header[len('Bearer '):].strip()
            if not token:
                return None
            if '.' in token:
                return None
            return token

        return None

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token = self._extract_token(auth_header)
        if not token:
            return None

        try:
            session = BrokerSession.objects.select_related('broker').get(token=token)
        except BrokerSession.DoesNotExist:
            raise AuthenticationFailed('Invalid broker token.')

        if not session.is_valid():
            session.delete()
            raise AuthenticationFailed('Broker token has expired. Please login again.')

        if session.broker.status != 'ACTIVE':
            raise AuthenticationFailed('Broker account is not active.')

        # Attach broker to request for use in views
        request.broker = session.broker
        request.tenant_id = session.broker.tenant_id
        return (session.broker, session)

    def authenticate_header(self, request):
        return self.keyword
