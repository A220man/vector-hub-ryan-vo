import asyncio
import time
import pytest
from fastapi import HTTPException
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from app.config import settings
from app.core.security import OIDCClient

@pytest.fixture
def issuer(monkeypatch):
    monkeypatch.setattr(settings, 'oidc_issuer', 'http://keycloak:8080/realms/vectorhub')
    monkeypatch.setattr(settings, 'oidc_external_issuer', 'https://login.example/realms/vectorhub')
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    client = OIDCClient()
    async def keys(): return public
    monkeypatch.setattr(client, 'get_jwks', keys)
    def token(iss):
        now = int(time.time())
        return jwt.encode({'sub': 'user', 'iss': iss, 'aud': settings.oidc_audience, 'iat': now, 'exp': now + 120, 'realm_access': {'roles': ['viewer']}}, private, algorithm='RS256')
    return client, token

def test_public_issuer_is_valid_even_when_transport_uses_docker_hostname(issuer):
    client, token = issuer
    user = asyncio.run(client.validate_token(token(settings.oidc_external_issuer)))
    assert user.sub == 'user'
    assert user.iss == settings.oidc_external_issuer

def test_internal_transport_hostname_is_not_an_accepted_token_issuer(issuer):
    client, token = issuer
    with pytest.raises(HTTPException) as error:
        asyncio.run(client.validate_token(token(settings.oidc_issuer)))
    assert error.value.status_code == 401

def test_single_host_configuration_still_validates_issuer(issuer, monkeypatch):
    client, token = issuer
    monkeypatch.setattr(settings, 'oidc_external_issuer', '')
    assert asyncio.run(client.validate_token(token(settings.oidc_issuer))).sub == 'user'
    with pytest.raises(HTTPException):
        asyncio.run(client.validate_token(token('https://wrong.example')))
