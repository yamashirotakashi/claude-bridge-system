"""
Claude Bridge System - Secure Communication Channel
セキュアな通信チャネル管理
"""

import asyncio
import logging
import ssl
import socket
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.x509 import load_pem_x509_certificate
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import secrets
import base64
import json

logger = logging.getLogger(__name__)


class EncryptionAlgorithm(Enum):
    """暗号化アルゴリズム"""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    RSA_OAEP = "rsa-oaep"


class CertificateType(Enum):
    """証明書タイプ"""
    SELF_SIGNED = "self_signed"
    CA_SIGNED = "ca_signed"
    CLIENT_CERT = "client_cert"
    SERVER_CERT = "server_cert"


@dataclass
class TLSConfig:
    """TLS設定"""
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ca_file: Optional[str] = None
    verify_mode: str = "CERT_REQUIRED"
    protocol: str = "TLSv1_2"
    ciphers: Optional[str] = None
    check_hostname: bool = True
    client_cert_required: bool = False
    
    def to_ssl_context(self) -> ssl.SSLContext:
        """SSL Contextを生成"""
        # プロトコル設定
        if self.protocol == "TLSv1_3":
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.minimum_version = ssl.TLSVersion.TLSv1_3
        elif self.protocol == "TLSv1_2":
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        
        # 証明書設定
        if self.cert_file and self.key_file:
            context.load_cert_chain(self.cert_file, self.key_file)
        
        # CA証明書設定
        if self.ca_file:
            context.load_verify_locations(self.ca_file)
        
        # 検証モード設定
        if self.verify_mode == "CERT_REQUIRED":
            context.verify_mode = ssl.CERT_REQUIRED
        elif self.verify_mode == "CERT_OPTIONAL":
            context.verify_mode = ssl.CERT_OPTIONAL
        else:
            context.verify_mode = ssl.CERT_NONE
        
        # ホスト名検証
        context.check_hostname = self.check_hostname
        
        # 暗号スイート設定
        if self.ciphers:
            context.set_ciphers(self.ciphers)
        
        # クライアント証明書要求
        if self.client_cert_required:
            context.verify_mode = ssl.CERT_REQUIRED
        
        return context


@dataclass
class EncryptionContext:
    """暗号化コンテキスト"""
    algorithm: EncryptionAlgorithm
    key: bytes
    iv: Optional[bytes] = None
    tag: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EncryptionManager:
    """暗号化管理システム"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: 暗号化設定
        """
        self.config = config or {}
        self.default_algorithm = EncryptionAlgorithm(
            self.config.get('default_algorithm', 'aes-256-gcm')
        )
        
        # キー管理
        self.encryption_keys: Dict[str, bytes] = {}
        self.key_derivation_salt = secrets.token_bytes(16)
        
        logger.info("EncryptionManager initialized")
    
    def generate_key(self, algorithm: EncryptionAlgorithm) -> bytes:
        """暗号化キー生成"""
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            return secrets.token_bytes(32)  # 256 bits
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            return secrets.token_bytes(32)  # 256 bits
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            return secrets.token_bytes(32)  # 256 bits
        elif algorithm == EncryptionAlgorithm.RSA_OAEP:
            # RSAキーペア生成
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            return private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """パスワードからキー導出"""
        if salt is None:
            salt = self.key_derivation_salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        
        return kdf.derive(password.encode('utf-8'))
    
    def encrypt(self, 
                data: Union[str, bytes], 
                algorithm: Optional[EncryptionAlgorithm] = None,
                key: Optional[bytes] = None) -> Tuple[bytes, EncryptionContext]:
        """データ暗号化"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        algorithm = algorithm or self.default_algorithm
        key = key or self.generate_key(algorithm)
        
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            return self._encrypt_aes_gcm(data, key)
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            return self._encrypt_aes_cbc(data, key)
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            return self._encrypt_chacha20_poly1305(data, key)
        else:
            raise ValueError(f"Unsupported encryption algorithm: {algorithm}")
    
    def decrypt(self, 
                encrypted_data: bytes, 
                context: EncryptionContext) -> bytes:
        """データ復号化"""
        if context.algorithm == EncryptionAlgorithm.AES_256_GCM:
            return self._decrypt_aes_gcm(encrypted_data, context)
        elif context.algorithm == EncryptionAlgorithm.AES_256_CBC:
            return self._decrypt_aes_cbc(encrypted_data, context)
        elif context.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            return self._decrypt_chacha20_poly1305(encrypted_data, context)
        else:
            raise ValueError(f"Unsupported decryption algorithm: {context.algorithm}")
    
    def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> Tuple[bytes, EncryptionContext]:
        """AES-GCM暗号化"""
        iv = secrets.token_bytes(12)  # GCMモードでは96ビットIVが推奨
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv)
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        context = EncryptionContext(
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key=key,
            iv=iv,
            tag=encryptor.tag
        )
        
        return ciphertext, context
    
    def _decrypt_aes_gcm(self, encrypted_data: bytes, context: EncryptionContext) -> bytes:
        """AES-GCM復号化"""
        cipher = Cipher(
            algorithms.AES(context.key),
            modes.GCM(context.iv, context.tag)
        )
        
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data) + decryptor.finalize()
    
    def _encrypt_aes_cbc(self, data: bytes, key: bytes) -> Tuple[bytes, EncryptionContext]:
        """AES-CBC暗号化"""
        iv = secrets.token_bytes(16)  # CBCモードでは128ビットIV
        
        # PKCS7パディング
        padding_length = 16 - (len(data) % 16)
        padded_data = data + bytes([padding_length] * padding_length)
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv)
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        context = EncryptionContext(
            algorithm=EncryptionAlgorithm.AES_256_CBC,
            key=key,
            iv=iv
        )
        
        return ciphertext, context
    
    def _decrypt_aes_cbc(self, encrypted_data: bytes, context: EncryptionContext) -> bytes:
        """AES-CBC復号化"""
        cipher = Cipher(
            algorithms.AES(context.key),
            modes.CBC(context.iv)
        )
        
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # PKCS7パディング除去
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]
    
    def _encrypt_chacha20_poly1305(self, data: bytes, key: bytes) -> Tuple[bytes, EncryptionContext]:
        """ChaCha20-Poly1305暗号化"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        nonce = secrets.token_bytes(12)
        chacha = ChaCha20Poly1305(key)
        ciphertext = chacha.encrypt(nonce, data, None)
        
        context = EncryptionContext(
            algorithm=EncryptionAlgorithm.CHACHA20_POLY1305,
            key=key,
            iv=nonce
        )
        
        return ciphertext, context
    
    def _decrypt_chacha20_poly1305(self, encrypted_data: bytes, context: EncryptionContext) -> bytes:
        """ChaCha20-Poly1305復号化"""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        chacha = ChaCha20Poly1305(context.key)
        return chacha.decrypt(context.iv, encrypted_data, None)


class CertificateManager:
    """証明書管理システム"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初期化"""
        self.config = config or {}
        self.certificates: Dict[str, Any] = {}
        self.cert_directory = Path(self.config.get('cert_directory', './certs'))
        self.cert_directory.mkdir(exist_ok=True)
        
        logger.info("CertificateManager initialized")
    
    def load_certificate(self, cert_path: Union[str, Path]) -> Any:
        """証明書読み込み"""
        cert_path = Path(cert_path)
        
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            certificate = load_pem_x509_certificate(cert_data)
            
            cert_id = cert_path.stem
            self.certificates[cert_id] = {
                'certificate': certificate,
                'path': cert_path,
                'subject': certificate.subject.rfc4514_string(),
                'issuer': certificate.issuer.rfc4514_string(),
                'not_before': certificate.not_valid_before,
                'not_after': certificate.not_valid_after,
                'serial_number': str(certificate.serial_number)
            }
            
            logger.info(f"Certificate loaded: {cert_id}")
            return certificate
            
        except Exception as e:
            logger.error(f"Failed to load certificate {cert_path}: {e}")
            raise
    
    def validate_certificate(self, cert_id: str) -> Dict[str, Any]:
        """証明書検証"""
        if cert_id not in self.certificates:
            return {'valid': False, 'error': 'Certificate not found'}
        
        cert_info = self.certificates[cert_id]
        certificate = cert_info['certificate']
        
        from datetime import datetime
        now = datetime.now()
        
        # 有効期限チェック
        if now < cert_info['not_before']:
            return {'valid': False, 'error': 'Certificate not yet valid'}
        
        if now > cert_info['not_after']:
            return {'valid': False, 'error': 'Certificate expired'}
        
        # 基本的な検証
        try:
            # 自己署名証明書の場合の検証
            public_key = certificate.public_key()
            # より詳細な検証は実装を簡略化
            
            return {
                'valid': True,
                'subject': cert_info['subject'],
                'issuer': cert_info['issuer'],
                'expires_at': cert_info['not_after'].isoformat(),
                'serial_number': cert_info['serial_number']
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation failed: {e}'}
    
    def generate_self_signed_cert(self, 
                                 common_name: str,
                                 validity_days: int = 365) -> Tuple[str, str]:
        """自己署名証明書生成"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta
        
        # 秘密鍵生成
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # 証明書生成
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Claude Bridge System"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security")
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(common_name),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # ファイル保存
        cert_path = self.cert_directory / f"{common_name}.pem"
        key_path = self.cert_directory / f"{common_name}.key"
        
        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger.info(f"Self-signed certificate generated: {common_name}")
        return str(cert_path), str(key_path)


class SecureChannelManager:
    """セキュア通信チャネル管理"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初期化"""
        self.config = config or {}
        self.encryption_manager = EncryptionManager(config.get('encryption', {}))
        self.certificate_manager = CertificateManager(config.get('certificates', {}))
        
        # TLS設定
        self.default_tls_config = TLSConfig(**config.get('tls', {}))
        
        # アクティブチャネル
        self.active_channels: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SecureChannelManager initialized")
    
    async def create_secure_server(self,
                                 host: str,
                                 port: int,
                                 handler: callable,
                                 tls_config: Optional[TLSConfig] = None) -> asyncio.Server:
        """セキュアサーバー作成"""
        tls_config = tls_config or self.default_tls_config
        ssl_context = tls_config.to_ssl_context()
        
        server = await asyncio.start_server(
            handler,
            host,
            port,
            ssl=ssl_context
        )
        
        channel_id = f"{host}:{port}"
        self.active_channels[channel_id] = {
            'type': 'server',
            'server': server,
            'host': host,
            'port': port,
            'tls_config': tls_config,
            'created_at': asyncio.get_event_loop().time()
        }
        
        logger.info(f"Secure server created: {channel_id}")
        return server
    
    async def create_secure_connection(self,
                                     host: str,
                                     port: int,
                                     tls_config: Optional[TLSConfig] = None) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """セキュア接続作成"""
        tls_config = tls_config or self.default_tls_config
        ssl_context = tls_config.to_ssl_context()
        
        reader, writer = await asyncio.open_connection(
            host,
            port,
            ssl=ssl_context
        )
        
        channel_id = f"client_{host}:{port}_{int(asyncio.get_event_loop().time())}"
        self.active_channels[channel_id] = {
            'type': 'client',
            'reader': reader,
            'writer': writer,
            'host': host,
            'port': port,
            'tls_config': tls_config,
            'created_at': asyncio.get_event_loop().time()
        }
        
        logger.info(f"Secure connection created: {channel_id}")
        return reader, writer
    
    def encrypt_message(self, 
                       message: Union[str, Dict[str, Any]],
                       algorithm: Optional[EncryptionAlgorithm] = None) -> Dict[str, str]:
        """メッセージ暗号化"""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        encrypted_data, context = self.encryption_manager.encrypt(message, algorithm)
        
        # Base64エンコード
        encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
        key_b64 = base64.b64encode(context.key).decode('utf-8')
        iv_b64 = base64.b64encode(context.iv).decode('utf-8') if context.iv else None
        tag_b64 = base64.b64encode(context.tag).decode('utf-8') if context.tag else None
        
        return {
            'encrypted_data': encrypted_b64,
            'algorithm': context.algorithm.value,
            'key': key_b64,
            'iv': iv_b64,
            'tag': tag_b64
        }
    
    def decrypt_message(self, encrypted_message: Dict[str, str]) -> str:
        """メッセージ復号化"""
        # Base64デコード
        encrypted_data = base64.b64decode(encrypted_message['encrypted_data'])
        key = base64.b64decode(encrypted_message['key'])
        iv = base64.b64decode(encrypted_message['iv']) if encrypted_message.get('iv') else None
        tag = base64.b64decode(encrypted_message['tag']) if encrypted_message.get('tag') else None
        
        # 復号化コンテキスト構築
        context = EncryptionContext(
            algorithm=EncryptionAlgorithm(encrypted_message['algorithm']),
            key=key,
            iv=iv,
            tag=tag
        )
        
        # 復号化
        decrypted_data = self.encryption_manager.decrypt(encrypted_data, context)
        return decrypted_data.decode('utf-8')
    
    async def send_secure_message(self,
                                writer: asyncio.StreamWriter,
                                message: Union[str, Dict[str, Any]],
                                encrypt: bool = True) -> None:
        """セキュアメッセージ送信"""
        if encrypt:
            encrypted_message = self.encrypt_message(message)
            data = json.dumps(encrypted_message).encode('utf-8')
        else:
            if isinstance(message, dict):
                data = json.dumps(message).encode('utf-8')
            else:
                data = message.encode('utf-8')
        
        # メッセージ長を先頭に付加
        length = len(data)
        length_bytes = length.to_bytes(4, byteorder='big')
        
        writer.write(length_bytes + data)
        await writer.drain()
    
    async def receive_secure_message(self,
                                   reader: asyncio.StreamReader,
                                   decrypt: bool = True) -> Union[str, Dict[str, Any]]:
        """セキュアメッセージ受信"""
        # メッセージ長読み取り
        length_bytes = await reader.read(4)
        if not length_bytes:
            raise ConnectionError("Connection closed")
        
        length = int.from_bytes(length_bytes, byteorder='big')
        
        # メッセージ本体読み取り
        data = await reader.read(length)
        if len(data) != length:
            raise ConnectionError("Incomplete message received")
        
        if decrypt:
            try:
                encrypted_message = json.loads(data.decode('utf-8'))
                return self.decrypt_message(encrypted_message)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to decrypt message: {e}")
                # 平文として扱う
                return data.decode('utf-8')
        else:
            try:
                return json.loads(data.decode('utf-8'))
            except json.JSONDecodeError:
                return data.decode('utf-8')
    
    def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """チャネル状態取得"""
        status = {}
        
        for channel_id, channel_info in self.active_channels.items():
            status[channel_id] = {
                'type': channel_info['type'],
                'host': channel_info['host'],
                'port': channel_info['port'],
                'created_at': channel_info['created_at'],
                'uptime_seconds': asyncio.get_event_loop().time() - channel_info['created_at']
            }
        
        return status
    
    async def close_channel(self, channel_id: str) -> bool:
        """チャネル閉鎖"""
        if channel_id not in self.active_channels:
            return False
        
        channel_info = self.active_channels[channel_id]
        
        try:
            if channel_info['type'] == 'server':
                server = channel_info['server']
                server.close()
                await server.wait_closed()
            elif channel_info['type'] == 'client':
                writer = channel_info['writer']
                writer.close()
                await writer.wait_closed()
            
            del self.active_channels[channel_id]
            logger.info(f"Channel closed: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing channel {channel_id}: {e}")
            return False


# グローバルインスタンス（遅延初期化用）
global_encryption_manager = None
global_certificate_manager = None
global_secure_channel_manager = None

def get_global_encryption_manager():
    global global_encryption_manager
    if global_encryption_manager is None:
        global_encryption_manager = EncryptionManager()
    return global_encryption_manager

def get_global_certificate_manager():
    global global_certificate_manager
    if global_certificate_manager is None:
        global_certificate_manager = CertificateManager()
    return global_certificate_manager

def get_global_secure_channel_manager():
    global global_secure_channel_manager
    if global_secure_channel_manager is None:
        global_secure_channel_manager = SecureChannelManager()
    return global_secure_channel_manager