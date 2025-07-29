"""
Claude Bridge System - Authentication & Authorization
認証・認可システム
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union, Callable
from dataclasses import dataclass, asdict
import jwt
import bcrypt
from pathlib import Path

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """認証方式"""
    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    OAUTH2 = "oauth2"
    MUTUAL_TLS = "mutual_tls"
    SESSION = "session"


class Permission(Enum):
    """権限レベル"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    SYSTEM = "system"


class Resource(Enum):
    """リソース種別"""
    PROJECT = "project"
    FILE = "file"
    CONFIG = "config"
    SYSTEM = "system"
    API = "api"
    DESKTOP_CONNECTION = "desktop_connection"
    MIS_MEMORY = "mis_memory"
    MONITORING = "monitoring"


@dataclass
class User:
    """ユーザー情報"""
    user_id: str
    username: str
    email: Optional[str] = None
    roles: List[str] = None
    permissions: List[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class AuthToken:
    """認証トークン"""
    token: str
    user_id: str
    token_type: str
    expires_at: str
    scopes: List[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []
        if self.metadata is None:
            self.metadata = {}
    
    def is_expired(self) -> bool:
        """トークン有効期限チェック"""
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now() > expires
        except ValueError:
            return True
    
    def has_scope(self, scope: str) -> bool:
        """スコープ確認"""
        return scope in self.scopes


@dataclass
class SecurityContext:
    """セキュリティコンテキスト"""
    user: Optional[User] = None
    token: Optional[AuthToken] = None
    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    permissions: Set[str] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()
    
    def is_authenticated(self) -> bool:
        """認証済みかチェック"""
        return self.user is not None and (
            self.token is None or not self.token.is_expired()
        )
    
    def has_permission(self, permission: str) -> bool:
        """権限確認"""
        return permission in self.permissions
    
    def has_role(self, role: str) -> bool:
        """ロール確認"""
        return self.user is not None and role in self.user.roles


class AuthenticationManager:
    """認証管理システム"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: 認証設定
        """
        self.config = config or {}
        self.users: Dict[str, User] = {}
        self.user_credentials: Dict[str, Dict[str, Any]] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> user_id
        self.sessions: Dict[str, SecurityContext] = {}
        
        # JWT設定
        self.jwt_secret = self.config.get('jwt_secret', secrets.token_urlsafe(32))
        self.jwt_algorithm = self.config.get('jwt_algorithm', 'HS256')
        self.jwt_expiry_hours = self.config.get('jwt_expiry_hours', 24)
        
        # セッション設定
        self.session_timeout_minutes = self.config.get('session_timeout_minutes', 60)
        
        # ブルートフォース対策
        self.max_failed_attempts = self.config.get('max_failed_attempts', 5)
        self.lockout_duration_minutes = self.config.get('lockout_duration_minutes', 15)
        self.failed_attempts: Dict[str, List[float]] = {}
        
        logger.info("AuthenticationManager initialized")
    
    def register_user(self, 
                     username: str, 
                     password: str, 
                     email: Optional[str] = None,
                     roles: Optional[List[str]] = None) -> User:
        """ユーザー登録"""
        user_id = self._generate_user_id()
        
        # パスワードハッシュ化
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            roles=roles or ['user']
        )
        
        self.users[user_id] = user
        self.user_credentials[user_id] = {
            'password_hash': password_hash,
            'auth_methods': [AuthMethod.SESSION.value, AuthMethod.API_KEY.value]
        }
        
        logger.info(f"User registered: {username} ({user_id})")
        return user
    
    def authenticate_password(self, username: str, password: str) -> Optional[User]:
        """パスワード認証"""
        # ユーザー検索
        user = self._find_user_by_username(username)
        if not user or not user.is_active:
            self._record_failed_attempt(username)
            return None
        
        # ロックアウトチェック
        if self._is_locked_out(username):
            logger.warning(f"Authentication blocked due to lockout: {username}")
            return None
        
        # パスワード検証
        credentials = self.user_credentials.get(user.user_id)
        if not credentials:
            self._record_failed_attempt(username)
            return None
        
        password_hash = credentials['password_hash']
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
            self._record_failed_attempt(username)
            return None
        
        # 認証成功
        self._clear_failed_attempts(username)
        user.last_login = datetime.now().isoformat()
        
        logger.info(f"Password authentication successful: {username}")
        return user
    
    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """APIキー認証"""
        user_id = self.api_keys.get(api_key)
        if not user_id:
            return None
        
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return None
        
        user.last_login = datetime.now().isoformat()
        logger.info(f"API key authentication successful: {user.username}")
        return user
    
    def authenticate_jwt(self, token: str) -> Optional[User]:
        """JWT認証"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id = payload.get('user_id')
            
            if not user_id:
                return None
            
            user = self.users.get(user_id)
            if not user or not user.is_active:
                return None
            
            # トークン有効期限チェック
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                return None
            
            user.last_login = datetime.now().isoformat()
            logger.info(f"JWT authentication successful: {user.username}")
            return user
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT authentication failed: {e}")
            return None
    
    def create_jwt_token(self, user: User, scopes: Optional[List[str]] = None) -> str:
        """JWTトークン生成"""
        now = datetime.now()
        expiry = now + timedelta(hours=self.jwt_expiry_hours)
        
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'roles': user.roles,
            'scopes': scopes or [],
            'iat': int(now.timestamp()),
            'exp': int(expiry.timestamp())
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        logger.info(f"JWT token created for user: {user.username}")
        return token
    
    def create_api_key(self, user: User) -> str:
        """APIキー生成"""
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = user.user_id
        
        logger.info(f"API key created for user: {user.username}")
        return api_key
    
    def revoke_api_key(self, api_key: str) -> bool:
        """APIキー無効化"""
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            logger.info("API key revoked")
            return True
        return False
    
    def create_session(self, user: User, client_ip: Optional[str] = None) -> str:
        """セッション作成"""
        session_id = secrets.token_urlsafe(32)
        
        context = SecurityContext(
            user=user,
            session_id=session_id,
            client_ip=client_ip
        )
        
        self.sessions[session_id] = context
        logger.info(f"Session created for user: {user.username}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SecurityContext]:
        """セッション取得"""
        context = self.sessions.get(session_id)
        if not context:
            return None
        
        # セッションタイムアウトチェック
        # 実装簡略化のため省略
        
        return context
    
    def revoke_session(self, session_id: str) -> bool:
        """セッション無効化"""
        if session_id in self.sessions:
            user = self.sessions[session_id].user
            del self.sessions[session_id]
            logger.info(f"Session revoked for user: {user.username if user else 'unknown'}")
            return True
        return False
    
    def _generate_user_id(self) -> str:
        """ユーザーID生成"""
        return f"user_{secrets.token_hex(8)}"
    
    def _find_user_by_username(self, username: str) -> Optional[User]:
        """ユーザー名でユーザー検索"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def _record_failed_attempt(self, identifier: str) -> None:
        """認証失敗記録"""
        now = time.time()
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = []
        
        self.failed_attempts[identifier].append(now)
        
        # 古い記録を削除（過去24時間のみ保持）
        cutoff = now - (24 * 60 * 60)
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier]
            if attempt > cutoff
        ]
    
    def _clear_failed_attempts(self, identifier: str) -> None:
        """認証失敗記録クリア"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
    
    def _is_locked_out(self, identifier: str) -> bool:
        """ロックアウト状態チェック"""
        if identifier not in self.failed_attempts:
            return False
        
        attempts = self.failed_attempts[identifier]
        if len(attempts) < self.max_failed_attempts:
            return False
        
        # 最新の失敗時刻をチェック
        last_attempt = max(attempts)
        lockout_end = last_attempt + (self.lockout_duration_minutes * 60)
        
        return time.time() < lockout_end


class AuthorizationManager:
    """認可管理システム"""
    
    def __init__(self):
        """初期化"""
        self.role_permissions: Dict[str, Set[str]] = {}
        self.resource_policies: Dict[str, List[Dict[str, Any]]] = {}
        
        # デフォルトロール設定
        self._setup_default_roles()
        
        logger.info("AuthorizationManager initialized")
    
    def _setup_default_roles(self) -> None:
        """デフォルトロール設定"""
        self.role_permissions = {
            'admin': {
                'system:read', 'system:write', 'system:execute', 'system:admin',
                'project:read', 'project:write', 'project:execute',
                'config:read', 'config:write',
                'monitoring:read', 'monitoring:write',
                'desktop_connection:read', 'desktop_connection:write',
                'mis_memory:read', 'mis_memory:write'
            },
            'user': {
                'project:read', 'project:write',
                'desktop_connection:read', 'desktop_connection:write',
                'mis_memory:read', 'mis_memory:write'
            },
            'readonly': {
                'project:read',
                'monitoring:read'
            },
            'system': {
                'system:read', 'system:write', 'system:execute', 'system:admin'
            }
        }
    
    def check_permission(self, context: SecurityContext, resource: str, action: str) -> bool:
        """権限チェック"""
        if not context.is_authenticated():
            return False
        
        permission = f"{resource}:{action}"
        
        # 直接権限チェック
        if context.has_permission(permission):
            return True
        
        # ロールベース権限チェック
        user_permissions = set()
        for role in context.user.roles:
            role_perms = self.role_permissions.get(role, set())
            user_permissions.update(role_perms)
        
        return permission in user_permissions
    
    def grant_permission(self, role: str, resource: str, action: str) -> None:
        """権限付与"""
        if role not in self.role_permissions:
            self.role_permissions[role] = set()
        
        permission = f"{resource}:{action}"
        self.role_permissions[role].add(permission)
        
        logger.info(f"Permission granted: {role} -> {permission}")
    
    def revoke_permission(self, role: str, resource: str, action: str) -> None:
        """権限取り消し"""
        if role not in self.role_permissions:
            return
        
        permission = f"{resource}:{action}"
        self.role_permissions[role].discard(permission)
        
        logger.info(f"Permission revoked: {role} -> {permission}")
    
    def get_user_permissions(self, user: User) -> Set[str]:
        """ユーザー権限取得"""
        permissions = set(user.permissions)
        
        for role in user.roles:
            role_perms = self.role_permissions.get(role, set())
            permissions.update(role_perms)
        
        return permissions


class TokenManager:
    """トークン管理システム"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初期化"""
        self.config = config or {}
        self.tokens: Dict[str, AuthToken] = {}
        self.refresh_tokens: Dict[str, str] = {}  # refresh_token -> access_token
        
        # 設定
        self.access_token_expiry_minutes = self.config.get('access_token_expiry_minutes', 60)
        self.refresh_token_expiry_days = self.config.get('refresh_token_expiry_days', 30)
        
        logger.info("TokenManager initialized")
    
    def create_token_pair(self, user: User, scopes: Optional[List[str]] = None) -> Dict[str, str]:
        """アクセストークン・リフレッシュトークンのペア生成"""
        # アクセストークン
        access_token = secrets.token_urlsafe(32)
        access_expires = datetime.now() + timedelta(minutes=self.access_token_expiry_minutes)
        
        auth_token = AuthToken(
            token=access_token,
            user_id=user.user_id,
            token_type='access',
            expires_at=access_expires.isoformat(),
            scopes=scopes or []
        )
        
        self.tokens[access_token] = auth_token
        
        # リフレッシュトークン
        refresh_token = secrets.token_urlsafe(32)
        refresh_expires = datetime.now() + timedelta(days=self.refresh_token_expiry_days)
        
        refresh_auth_token = AuthToken(
            token=refresh_token,
            user_id=user.user_id,
            token_type='refresh',
            expires_at=refresh_expires.isoformat()
        )
        
        self.tokens[refresh_token] = refresh_auth_token
        self.refresh_tokens[refresh_token] = access_token
        
        logger.info(f"Token pair created for user: {user.username}")
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': self.access_token_expiry_minutes * 60,
            'token_type': 'Bearer'
        }
    
    def validate_token(self, token: str) -> Optional[AuthToken]:
        """トークン検証"""
        auth_token = self.tokens.get(token)
        if not auth_token:
            return None
        
        if auth_token.is_expired():
            self.revoke_token(token)
            return None
        
        return auth_token
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """アクセストークン更新"""
        auth_token = self.validate_token(refresh_token)
        if not auth_token or auth_token.token_type != 'refresh':
            return None
        
        # 古いアクセストークンを無効化
        old_access_token = self.refresh_tokens.get(refresh_token)
        if old_access_token:
            self.revoke_token(old_access_token)
        
        # 新しいアクセストークン生成
        new_access_token = secrets.token_urlsafe(32)
        access_expires = datetime.now() + timedelta(minutes=self.access_token_expiry_minutes)
        
        new_auth_token = AuthToken(
            token=new_access_token,
            user_id=auth_token.user_id,
            token_type='access',
            expires_at=access_expires.isoformat(),
            scopes=auth_token.scopes
        )
        
        self.tokens[new_access_token] = new_auth_token
        self.refresh_tokens[refresh_token] = new_access_token
        
        logger.info(f"Access token refreshed for user: {auth_token.user_id}")
        return new_access_token
    
    def revoke_token(self, token: str) -> bool:
        """トークン無効化"""
        if token in self.tokens:
            del self.tokens[token]
            
            # リフレッシュトークンの場合、対応するアクセストークンも削除
            if token in self.refresh_tokens:
                access_token = self.refresh_tokens[token]
                if access_token in self.tokens:
                    del self.tokens[access_token]
                del self.refresh_tokens[token]
            
            # アクセストークンの場合、対応するリフレッシュトークンも削除
            for refresh_token, access_token in list(self.refresh_tokens.items()):
                if access_token == token:
                    del self.refresh_tokens[refresh_token]
                    if refresh_token in self.tokens:
                        del self.tokens[refresh_token]
                    break
            
            logger.info("Token revoked")
            return True
        
        return False
    
    def cleanup_expired_tokens(self) -> int:
        """期限切れトークンクリーンアップ"""
        expired_tokens = []
        
        for token, auth_token in self.tokens.items():
            if auth_token.is_expired():
                expired_tokens.append(token)
        
        for token in expired_tokens:
            self.revoke_token(token)
        
        logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
        return len(expired_tokens)


class PermissionManager:
    """権限管理システム"""
    
    def __init__(self):
        """初期化"""
        self.permission_cache: Dict[str, Dict[str, bool]] = {}  # user_id -> {permission -> bool}
        self.cache_ttl = 300  # 5分
        self.cache_timestamps: Dict[str, float] = {}
        
        logger.info("PermissionManager initialized")
    
    def check_cached_permission(self, user_id: str, permission: str) -> Optional[bool]:
        """キャッシュされた権限チェック"""
        if user_id not in self.permission_cache:
            return None
        
        # キャッシュ有効期限チェック
        timestamp = self.cache_timestamps.get(user_id, 0)
        if time.time() - timestamp > self.cache_ttl:
            self._clear_user_cache(user_id)
            return None
        
        return self.permission_cache[user_id].get(permission)
    
    def cache_permission(self, user_id: str, permission: str, result: bool) -> None:
        """権限結果をキャッシュ"""
        if user_id not in self.permission_cache:
            self.permission_cache[user_id] = {}
        
        self.permission_cache[user_id][permission] = result
        self.cache_timestamps[user_id] = time.time()
    
    def _clear_user_cache(self, user_id: str) -> None:
        """ユーザーキャッシュクリア"""
        if user_id in self.permission_cache:
            del self.permission_cache[user_id]
        if user_id in self.cache_timestamps:
            del self.cache_timestamps[user_id]


def require_auth(auth_method: AuthMethod = AuthMethod.JWT_TOKEN):
    """認証デコレーター"""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            # 実装簡略化のため、実際の認証チェックは省略
            return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # 実装簡略化のため、実際の認証チェックは省略
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def require_permission(resource: str, action: str):
    """権限チェックデコレーター"""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            # 実装簡略化のため、実際の権限チェックは省略
            return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # 実装簡略化のため、実際の権限チェックは省略
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# グローバルインスタンス（遅延初期化用）
global_auth_manager = None
global_authz_manager = None
global_token_manager = None
global_permission_manager = None

def get_global_auth_manager():
    global global_auth_manager
    if global_auth_manager is None:
        global_auth_manager = AuthenticationManager()
    return global_auth_manager

def get_global_authz_manager():
    global global_authz_manager
    if global_authz_manager is None:
        global_authz_manager = AuthorizationManager()
    return global_authz_manager

def get_global_token_manager():
    global global_token_manager
    if global_token_manager is None:
        global_token_manager = TokenManager()
    return global_token_manager

def get_global_permission_manager():
    global global_permission_manager
    if global_permission_manager is None:
        global_permission_manager = PermissionManager()
    return global_permission_manager