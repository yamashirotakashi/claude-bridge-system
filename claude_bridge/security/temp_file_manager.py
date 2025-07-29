#!/usr/bin/env python3
"""
Claude Bridge System - Temporary File Management and Auto-Cleanup
Secure temporary file handling with automatic cleanup
"""

import os
import tempfile
import time
import threading
import logging
import shutil
import stat
import fnmatch
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import json
import atexit


class CleanupStrategy(Enum):
    """Cleanup strategies"""
    IMMEDIATE = "immediate"  # Clean up immediately after use
    SESSION = "session"      # Clean up at end of session
    TIME_BASED = "time_based"  # Clean up after specified time
    SIZE_BASED = "size_based"  # Clean up when reaching size limit
    MANUAL = "manual"        # Manual cleanup only


@dataclass
class TempFileInfo:
    """Temporary file information"""
    file_path: str
    created_time: float
    last_accessed: float
    size_bytes: int
    cleanup_strategy: CleanupStrategy
    max_age_seconds: Optional[int] = None
    secure_delete: bool = False
    owner_session: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureTempFileManager:
    """Secure temporary file manager with automatic cleanup"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize temp file manager"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.base_temp_dir = self.config.get('base_temp_dir', tempfile.gettempdir())
        self.max_total_size = self.config.get('max_total_size_mb', 100) * 1024 * 1024  # MB to bytes
        self.default_max_age = self.config.get('default_max_age_seconds', 3600)  # 1 hour
        self.cleanup_interval = self.config.get('cleanup_interval_seconds', 300)  # 5 minutes
        self.secure_delete_default = self.config.get('secure_delete_default', True)
        
        # Internal state
        self.managed_files: Dict[str, TempFileInfo] = {}
        self.cleanup_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        self.lock = threading.RLock()
        
        # Create secure temp directory
        self.secure_temp_dir = self._create_secure_temp_dir()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Register cleanup on exit
        atexit.register(self._cleanup_all_files)

    def _create_secure_temp_dir(self) -> str:
        """Create secure temporary directory"""
        try:
            # Create secure temp directory with restricted permissions
            temp_dir = tempfile.mkdtemp(prefix="claude_bridge_secure_", dir=self.base_temp_dir)
            
            # Set secure permissions (owner only)
            os.chmod(temp_dir, stat.S_IRWXU)  # 700
            
            self.logger.info(f"Created secure temp directory: {temp_dir}")
            return temp_dir
            
        except Exception as e:
            self.logger.error(f"Failed to create secure temp directory: {e}")
            # Fallback to system temp
            return tempfile.gettempdir()

    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            return
            
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="TempFileCleanup",
            daemon=True
        )
        self.cleanup_thread.start()
        self.logger.info("Started temp file cleanup thread")

    def _cleanup_worker(self):
        """Background cleanup worker"""
        while not self.shutdown_event.wait(self.cleanup_interval):
            try:
                self._perform_periodic_cleanup()
            except Exception as e:
                self.logger.error(f"Error in cleanup worker: {e}")

    def create_temp_file(self, suffix: str = "", prefix: str = "claude_temp_", 
                        cleanup_strategy: CleanupStrategy = CleanupStrategy.SESSION,
                        max_age_seconds: Optional[int] = None,
                        secure_delete: Optional[bool] = None,
                        session_id: Optional[str] = None) -> Tuple[str, int]:
        """Create secure temporary file"""
        
        if secure_delete is None:
            secure_delete = self.secure_delete_default
            
        if max_age_seconds is None:
            max_age_seconds = self.default_max_age

        try:
            # Create temporary file in secure directory
            fd, file_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=self.secure_temp_dir
            )
            
            # Set secure permissions
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
            
            # Record file info
            current_time = time.time()
            file_info = TempFileInfo(
                file_path=file_path,
                created_time=current_time,
                last_accessed=current_time,
                size_bytes=0,
                cleanup_strategy=cleanup_strategy,
                max_age_seconds=max_age_seconds,
                secure_delete=secure_delete,
                owner_session=session_id,
                metadata={}
            )
            
            with self.lock:
                self.managed_files[file_path] = file_info
            
            self.logger.debug(f"Created temp file: {file_path}")
            return file_path, fd
            
        except Exception as e:
            self.logger.error(f"Failed to create temp file: {e}")
            raise

    def create_temp_directory(self, suffix: str = "", prefix: str = "claude_temp_dir_",
                            cleanup_strategy: CleanupStrategy = CleanupStrategy.SESSION,
                            max_age_seconds: Optional[int] = None,
                            secure_delete: Optional[bool] = None,
                            session_id: Optional[str] = None) -> str:
        """Create secure temporary directory"""
        
        if secure_delete is None:
            secure_delete = self.secure_delete_default
            
        if max_age_seconds is None:
            max_age_seconds = self.default_max_age

        try:
            # Create temporary directory in secure location
            dir_path = tempfile.mkdtemp(
                suffix=suffix,
                prefix=prefix,
                dir=self.secure_temp_dir
            )
            
            # Set secure permissions
            os.chmod(dir_path, stat.S_IRWXU)  # 700
            
            # Record directory info
            current_time = time.time()
            dir_info = TempFileInfo(
                file_path=dir_path,
                created_time=current_time,
                last_accessed=current_time,
                size_bytes=0,
                cleanup_strategy=cleanup_strategy,
                max_age_seconds=max_age_seconds,
                secure_delete=secure_delete,
                owner_session=session_id,
                metadata={"is_directory": True}
            )
            
            with self.lock:
                self.managed_files[dir_path] = dir_info
            
            self.logger.debug(f"Created temp directory: {dir_path}")
            return dir_path
            
        except Exception as e:
            self.logger.error(f"Failed to create temp directory: {e}")
            raise

    def register_temp_file(self, file_path: str, cleanup_strategy: CleanupStrategy = CleanupStrategy.SESSION,
                          max_age_seconds: Optional[int] = None,
                          secure_delete: Optional[bool] = None,
                          session_id: Optional[str] = None) -> bool:
        """Register existing file for management"""
        
        if not os.path.exists(file_path):
            self.logger.warning(f"Cannot register non-existent file: {file_path}")
            return False
            
        if secure_delete is None:
            secure_delete = self.secure_delete_default
            
        if max_age_seconds is None:
            max_age_seconds = self.default_max_age

        try:
            stat_info = os.stat(file_path)
            current_time = time.time()
            
            file_info = TempFileInfo(
                file_path=file_path,
                created_time=stat_info.st_ctime,
                last_accessed=current_time,
                size_bytes=stat_info.st_size,
                cleanup_strategy=cleanup_strategy,
                max_age_seconds=max_age_seconds,
                secure_delete=secure_delete,
                owner_session=session_id,
                metadata={"is_directory": stat.S_ISDIR(stat_info.st_mode)}
            )
            
            with self.lock:
                self.managed_files[file_path] = file_info
            
            self.logger.debug(f"Registered temp file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register temp file {file_path}: {e}")
            return False

    def update_access_time(self, file_path: str):
        """Update last access time for file"""
        with self.lock:
            if file_path in self.managed_files:
                self.managed_files[file_path].last_accessed = time.time()

    def cleanup_file(self, file_path: str, force: bool = False) -> bool:
        """Clean up specific file"""
        with self.lock:
            if file_path not in self.managed_files:
                self.logger.warning(f"File not managed: {file_path}")
                return False
                
            file_info = self.managed_files[file_path]
            
            # Check if immediate cleanup is needed
            if not force and file_info.cleanup_strategy == CleanupStrategy.MANUAL:
                self.logger.debug(f"Manual cleanup file, skipping: {file_path}")
                return False

        return self._delete_file_or_directory(file_path, file_info)

    def cleanup_session_files(self, session_id: str) -> int:
        """Clean up all files for a specific session"""
        cleaned_count = 0
        
        files_to_cleanup = []
        with self.lock:
            for file_path, file_info in self.managed_files.items():
                if file_info.owner_session == session_id:
                    files_to_cleanup.append(file_path)
        
        for file_path in files_to_cleanup:
            if self.cleanup_file(file_path, force=True):
                cleaned_count += 1
                
        self.logger.info(f"Cleaned up {cleaned_count} files for session {session_id}")
        return cleaned_count

    def _perform_periodic_cleanup(self):
        """Perform periodic cleanup based on strategies"""
        current_time = time.time()
        files_to_cleanup = []
        total_size = 0
        
        with self.lock:
            # Calculate total size and identify files for cleanup
            for file_path, file_info in list(self.managed_files.items()):
                # Update size if file still exists
                if os.path.exists(file_path):
                    try:
                        current_size = self._get_path_size(file_path)
                        file_info.size_bytes = current_size
                        total_size += current_size
                    except:
                        pass
                else:
                    # File no longer exists, remove from tracking
                    del self.managed_files[file_path]
                    continue
                
                # Check cleanup conditions
                should_cleanup = False
                
                if file_info.cleanup_strategy == CleanupStrategy.TIME_BASED:
                    if file_info.max_age_seconds:
                        age = current_time - file_info.created_time
                        if age > file_info.max_age_seconds:
                            should_cleanup = True
                            
                elif file_info.cleanup_strategy == CleanupStrategy.IMMEDIATE:
                    # Check if file hasn't been accessed recently (5 seconds)
                    if current_time - file_info.last_accessed > 5:
                        should_cleanup = True
                
                if should_cleanup:
                    files_to_cleanup.append(file_path)
            
            # Size-based cleanup if over limit
            if total_size > self.max_total_size:
                self.logger.warning(f"Total temp size ({total_size} bytes) exceeds limit ({self.max_total_size} bytes)")
                # Add oldest files to cleanup list
                oldest_files = sorted(
                    self.managed_files.items(),
                    key=lambda x: x[1].last_accessed
                )
                
                size_to_free = total_size - (self.max_total_size * 0.8)  # Free to 80% of limit
                freed_size = 0
                
                for file_path, file_info in oldest_files:
                    if file_path not in files_to_cleanup:
                        files_to_cleanup.append(file_path)
                        freed_size += file_info.size_bytes
                        if freed_size >= size_to_free:
                            break
        
        # Perform cleanup
        cleaned_count = 0
        for file_path in files_to_cleanup:
            if self.cleanup_file(file_path, force=True):
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"Periodic cleanup: removed {cleaned_count} files")

    def _delete_file_or_directory(self, path: str, file_info: TempFileInfo) -> bool:
        """Securely delete file or directory"""
        try:
            if not os.path.exists(path):
                # Already deleted, just remove from tracking
                with self.lock:
                    self.managed_files.pop(path, None)
                return True
                
            is_directory = file_info.metadata.get("is_directory", False) or os.path.isdir(path)
            
            if file_info.secure_delete and not is_directory:
                # Secure delete for files
                self._secure_delete_file(path)
            else:
                # Regular delete
                if is_directory:
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.unlink(path)
            
            # Remove from tracking
            with self.lock:
                self.managed_files.pop(path, None)
            
            self.logger.debug(f"Deleted temp {'directory' if is_directory else 'file'}: {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete {path}: {e}")
            return False

    def _secure_delete_file(self, file_path: str):
        """Securely delete file by overwriting with random data"""
        try:
            if not os.path.isfile(file_path):
                return
                
            file_size = os.path.getsize(file_path)
            
            # Overwrite with random data (3 passes)
            with open(file_path, 'r+b') as f:
                for _ in range(3):
                    f.seek(0)
                    # Write random data
                    random_data = os.urandom(min(file_size, 64 * 1024))  # 64KB chunks
                    bytes_written = 0
                    while bytes_written < file_size:
                        chunk_size = min(len(random_data), file_size - bytes_written)
                        f.write(random_data[:chunk_size])
                        bytes_written += chunk_size
                    f.flush()
                    os.fsync(f.fileno())
            
            # Finally delete the file
            os.unlink(file_path)
            
        except Exception as e:
            self.logger.error(f"Secure delete failed for {file_path}: {e}")
            # Fallback to regular delete
            try:
                os.unlink(file_path)
            except:
                pass

    def _get_path_size(self, path: str) -> int:
        """Get size of file or directory"""
        if os.path.isfile(path):
            return os.path.getsize(path)
        elif os.path.isdir(path):
            total_size = 0
            try:
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        file_path = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(file_path)
                        except:
                            pass
            except:
                pass
            return total_size
        return 0

    def get_managed_files_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all managed files"""
        info = {}
        current_time = time.time()
        
        with self.lock:
            for file_path, file_info in self.managed_files.items():
                # Update current size
                current_size = 0
                exists = False
                if os.path.exists(file_path):
                    exists = True
                    try:
                        current_size = self._get_path_size(file_path)
                        file_info.size_bytes = current_size
                    except:
                        pass
                
                info[file_path] = {
                    "exists": exists,
                    "size_bytes": current_size,
                    "age_seconds": current_time - file_info.created_time,
                    "last_accessed_seconds_ago": current_time - file_info.last_accessed,
                    "cleanup_strategy": file_info.cleanup_strategy.value,
                    "max_age_seconds": file_info.max_age_seconds,
                    "secure_delete": file_info.secure_delete,
                    "owner_session": file_info.owner_session,
                    "is_directory": file_info.metadata.get("is_directory", False)
                }
        
        return info

    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics"""
        current_time = time.time()
        total_files = 0
        total_directories = 0
        total_size = 0
        by_strategy = {}
        by_session = {}
        oldest_file = None
        newest_file = None
        
        with self.lock:
            for file_path, file_info in self.managed_files.items():
                if file_info.metadata.get("is_directory", False):
                    total_directories += 1
                else:
                    total_files += 1
                
                total_size += file_info.size_bytes
                
                # By strategy
                strategy = file_info.cleanup_strategy.value
                by_strategy[strategy] = by_strategy.get(strategy, 0) + 1
                
                # By session
                session = file_info.owner_session or "no_session"
                by_session[session] = by_session.get(session, 0) + 1
                
                # Age tracking
                if oldest_file is None or file_info.created_time < oldest_file:
                    oldest_file = file_info.created_time
                if newest_file is None or file_info.created_time > newest_file:
                    newest_file = file_info.created_time
        
        return {
            "total_managed_files": total_files,
            "total_managed_directories": total_directories,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "size_limit_mb": round(self.max_total_size / (1024 * 1024), 2),
            "size_utilization_percent": round((total_size / self.max_total_size) * 100, 2) if self.max_total_size > 0 else 0,
            "by_cleanup_strategy": by_strategy,
            "by_session": by_session,
            "oldest_file_age_hours": round((current_time - oldest_file) / 3600, 2) if oldest_file else 0,
            "newest_file_age_hours": round((current_time - newest_file) / 3600, 2) if newest_file else 0,
            "secure_temp_dir": self.secure_temp_dir,
            "cleanup_thread_alive": self.cleanup_thread.is_alive() if self.cleanup_thread else False
        }

    def _cleanup_all_files(self):
        """Clean up all managed files (called on exit)"""
        self.logger.info("Cleaning up all managed temp files")
        
        # Stop cleanup thread
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.shutdown_event.set()
            self.cleanup_thread.join(timeout=5)
        
        # Clean up all files
        files_to_cleanup = list(self.managed_files.keys())
        cleaned_count = 0
        
        for file_path in files_to_cleanup:
            if self.cleanup_file(file_path, force=True):
                cleaned_count += 1
        
        # Clean up secure temp directory
        try:
            if os.path.exists(self.secure_temp_dir) and self.secure_temp_dir != tempfile.gettempdir():
                shutil.rmtree(self.secure_temp_dir, ignore_errors=True)
                self.logger.info(f"Removed secure temp directory: {self.secure_temp_dir}")
        except Exception as e:
            self.logger.error(f"Failed to remove secure temp directory: {e}")
        
        self.logger.info(f"Cleanup complete: removed {cleaned_count} files")

    def force_cleanup_all(self) -> int:
        """Force cleanup of all managed files"""
        files_to_cleanup = list(self.managed_files.keys())
        cleaned_count = 0
        
        for file_path in files_to_cleanup:
            if self.cleanup_file(file_path, force=True):
                cleaned_count += 1
        
        return cleaned_count

    def cleanup_by_pattern(self, pattern: str) -> int:
        """Clean up files matching a pattern"""
        files_to_cleanup = []
        
        with self.lock:
            for file_path in self.managed_files.keys():
                if fnmatch.fnmatch(os.path.basename(file_path), pattern):
                    files_to_cleanup.append(file_path)
        
        cleaned_count = 0
        for file_path in files_to_cleanup:
            if self.cleanup_file(file_path, force=True):
                cleaned_count += 1
        
        return cleaned_count

    def cleanup_older_than(self, max_age_seconds: int) -> int:
        """Clean up files older than specified age"""
        current_time = time.time()
        files_to_cleanup = []
        
        with self.lock:
            for file_path, file_info in self.managed_files.items():
                age = current_time - file_info.created_time
                if age > max_age_seconds:
                    files_to_cleanup.append(file_path)
        
        cleaned_count = 0
        for file_path in files_to_cleanup:
            if self.cleanup_file(file_path, force=True):
                cleaned_count += 1
        
        return cleaned_count

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self._cleanup_all_files()


def main():
    """Demo temp file manager functionality"""
    print("🗂️ Secure Temporary File Manager Demo")
    print("=" * 50)
    
    # Create temp file manager
    config = {
        'max_total_size_mb': 1,  # 1MB limit for demo
        'default_max_age_seconds': 30,  # 30 seconds for demo
        'cleanup_interval_seconds': 10,  # 10 seconds for demo
        'secure_delete_default': True
    }
    
    temp_manager = SecureTempFileManager(config)
    
    try:
        # Create some temp files
        print("\n📁 Creating temporary files...")
        
        # Session-based cleanup
        session_file, fd1 = temp_manager.create_temp_file(
            suffix=".txt",
            prefix="session_test_",
            cleanup_strategy=CleanupStrategy.SESSION,
            session_id="test_session_1"
        )
        os.write(fd1, b"This is a session-based temp file")
        os.close(fd1)
        print(f"Created session file: {os.path.basename(session_file)}")
        
        # Time-based cleanup
        time_file, fd2 = temp_manager.create_temp_file(
            suffix=".log",
            prefix="time_test_",
            cleanup_strategy=CleanupStrategy.TIME_BASED,
            max_age_seconds=15  # 15 seconds
        )
        os.write(fd2, b"This file will be cleaned up after 15 seconds")
        os.close(fd2)
        print(f"Created time-based file: {os.path.basename(time_file)}")
        
        # Immediate cleanup
        immediate_file, fd3 = temp_manager.create_temp_file(
            suffix=".tmp",
            prefix="immediate_test_",
            cleanup_strategy=CleanupStrategy.IMMEDIATE
        )
        os.write(fd3, b"This file will be cleaned up immediately after use")
        os.close(fd3)
        print(f"Created immediate file: {os.path.basename(immediate_file)}")
        
        # Create temp directory
        temp_dir = temp_manager.create_temp_directory(
            prefix="test_dir_",
            cleanup_strategy=CleanupStrategy.SESSION,
            session_id="test_session_1"
        )
        
        # Create some files in the directory
        for i in range(3):
            file_path = os.path.join(temp_dir, f"file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Content of file {i}")
        
        print(f"Created temp directory: {os.path.basename(temp_dir)} with 3 files")
        
        # Show initial statistics
        print(f"\n📊 Initial Statistics:")
        stats = temp_manager.get_statistics()
        print(f"Files: {stats['total_managed_files']}")
        print(f"Directories: {stats['total_managed_directories']}")
        print(f"Total Size: {stats['total_size_mb']} MB")
        print(f"Size Utilization: {stats['size_utilization_percent']}%")
        
        # Show file info
        print(f"\n📋 Managed Files:")
        files_info = temp_manager.get_managed_files_info()
        for file_path, info in files_info.items():
            name = os.path.basename(file_path)
            print(f"  {name}: {info['size_bytes']} bytes, {info['age_seconds']:.1f}s old, {info['cleanup_strategy']}")
        
        # Wait and let cleanup happen
        print(f"\n⏱️ Waiting for time-based cleanup (15 seconds)...")
        time.sleep(16)
        
        # Check statistics after cleanup
        print(f"\n📊 Statistics after time-based cleanup:")
        stats = temp_manager.get_statistics()
        print(f"Files: {stats['total_managed_files']}")
        print(f"Directories: {stats['total_managed_directories']}")
        print(f"Total Size: {stats['total_size_mb']} MB")
        
        # Manual cleanup of session files
        print(f"\n🧹 Cleaning up session files...")
        cleaned = temp_manager.cleanup_session_files("test_session_1")
        print(f"Cleaned {cleaned} session files")
        
        # Final statistics
        print(f"\n📊 Final Statistics:")
        stats = temp_manager.get_statistics()
        print(f"Files: {stats['total_managed_files']}")
        print(f"Directories: {stats['total_managed_directories']}")
        print(f"Total Size: {stats['total_size_mb']} MB")
        
        # Test pattern cleanup
        print(f"\n🎯 Testing pattern cleanup...")
        
        # Create some files with specific patterns
        for i in range(3):
            test_file, fd = temp_manager.create_temp_file(
                suffix=".test",
                prefix=f"pattern_test_{i}_",
                cleanup_strategy=CleanupStrategy.MANUAL
            )
            os.write(fd, f"Pattern test file {i}".encode())
            os.close(fd)
        
        print(f"Created 3 pattern test files")
        
        # Clean up files matching pattern
        cleaned = temp_manager.cleanup_by_pattern("pattern_test_*")
        print(f"Cleaned {cleaned} files matching pattern")
        
        # Test age-based cleanup
        print(f"\n⏰ Testing age-based cleanup...")
        
        # Create old file (simulate by modifying tracking info)
        old_file, fd = temp_manager.create_temp_file(prefix="old_test_")
        os.write(fd, b"This file will be made to look old")
        os.close(fd)
        
        # Manually modify the creation time to make it look old
        with temp_manager.lock:
            if old_file in temp_manager.managed_files:
                temp_manager.managed_files[old_file].created_time = time.time() - 3600  # 1 hour ago
        
        cleaned = temp_manager.cleanup_older_than(1800)  # 30 minutes
        print(f"Cleaned {cleaned} files older than 30 minutes")
        
    finally:
        # Force cleanup all remaining files
        print(f"\n🧹 Force cleaning all remaining files...")
        cleaned = temp_manager.force_cleanup_all()
        print(f"Force cleaned {cleaned} files")
        
        print(f"\n✅ Demo completed successfully!")


if __name__ == "__main__":
    main()