import time
from urllib.parse import urlparse, parse_qs
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from jose import jwt
from app.config import settings
from app.core import security as sec
from app.api.v1.auth import router

@pytest.fixture
def flow(monkeypatch):
    monkeypatch.setenv("DEMO_MODE","false")
    monkeypatch.setattr(settings,"demo_mode",False)
    monkeypatch.setattr(settings,"debug",True)
    sec._session_store.clear();sec._pkce_store.clear()
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    async def keys():return public
    monkeypatch.setattr(sec.oidc_client,'get_jwks',keys)
    state={'nonce':None,'bad_nonce':False,'missing_id':False,'subject_mismatch':False,'exchanges':0}
    async def exchange(code,verifier):
        state['exchanges']+=1
        import hashlib,base64
        assert base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')==state['challenge']
        now=int(time.time());base={'sub':'user-1','iss':settings.oidc_issuer,'iat':now,'exp':now+300,'realm_access':{'roles':['operator']}}
        identity={**base,'aud':settings.oidc_client_id,'nonce':'wrong' if state['bad_nonce'] else state['nonce']}
        if state['subject_mismatch']:identity['sub']='different-user'
        if state.get('wrong_id_audience'):identity['aud']='another-client'
        if state.get('expired_access'):base['exp']=now-60
        if state.get('missing_exp'):base.pop('exp')
        tokens={'access_token':jwt.encode({**base,'aud':settings.oidc_audience},private,algorithm='RS256')}
        if not state['missing_id']:tokens['id_token']=jwt.encode(identity,private,algorithm='RS256',access_token='wrong-access-token' if state.get('bad_at_hash') else tokens['access_token'])
        return tokens
    monkeypatch.setattr(sec.oidc_client,'exchange_code',exchange)
    app=FastAPI();app.include_router(router,prefix='/api/v1')
    @app.post('/write',dependencies=[Depends(sec.get_current_user),Depends(sec.verify_csrf)])
    def write():return {'saved':True}
    client=TestClient(app)
    def begin():
        response=client.get('/api/v1/auth/login');assert response.status_code==200
        query=parse_qs(urlparse(response.json()['auth_url']).query)
        state['nonce']=query['nonce'][0];state['challenge']=query['code_challenge'][0]
        return response.json()['state']
    return client,state,begin,app

def test_callback_cookie_authenticated_followup_and_csrf_write(flow):
    client,state,begin,_=flow;token=begin()
    response=client.get('/api/v1/auth/callback',params={'code':'valid','state':token},follow_redirects=False)
    assert response.status_code==303
    assert response.cookies.get(settings.session_cookie_name)
    assert client.get('/api/v1/auth/me').json()['sub']=='user-1'
    csrf=client.get('/api/v1/auth/csrf').json()['csrf_token']
    assert client.post('/write',headers={'X-CSRF-Token':csrf}).status_code==200
    assert client.post('/write',headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert client.get('/api/v1/auth/callback',params={'code':'valid','state':token},follow_redirects=False).status_code==400
    assert state['exchanges']==1

def test_state_cannot_be_used_by_another_browser(flow):
    client,state,begin,app=flow;token=begin()
    stranger=TestClient(app)
    assert stranger.get('/api/v1/auth/callback',params={'code':'valid','state':token}).status_code==400
    assert state['exchanges']==0
    assert client.get('/api/v1/auth/callback',params={'code':'valid','state':token},follow_redirects=False).status_code==303

@pytest.mark.parametrize('flag,expected',[('bad_at_hash',401),('bad_nonce',401),('missing_id',400),('subject_mismatch',401),('wrong_id_audience',401),('expired_access',401),('missing_exp',401)])
def test_invalid_identity_rejected(flow,flag,expected):
    client,state,begin,_=flow;token=begin();state[flag]=True
    r=client.get('/api/v1/auth/callback',params={'code':'valid','state':token},follow_redirects=False)
    assert r.status_code==expected
    assert not r.cookies.get(settings.session_cookie_name)
    assert client.get('/api/v1/auth/me').status_code==401

def test_expired_session_access_token_rejected(flow):
    client,_,_,_=flow
    sid=sec.create_session({'token_data': {'sub':'user-1','email':None,'name':None,'roles':['viewer'],'exp':int(time.time())-1,'iat':int(time.time())-600,'aud':settings.oidc_audience,'iss':settings.oidc_issuer}})
    client.cookies.set(settings.session_cookie_name,sid)
    assert client.get('/api/v1/auth/me').status_code==401
    assert sec.get_session(sid) is None

def test_expired_login_transaction_rejected(flow):
    client,state,begin,_=flow;token=begin()
    sid=client.cookies.get(settings.session_cookie_name+'_login')
    sec._session_store[sid]['created_at']=time.time()-601
    assert client.get('/api/v1/auth/callback',params={'code':'valid','state':token}).status_code==400
    assert state['exchanges']==0
