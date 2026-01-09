"""
데이터 백업/복원 시스템
로컬 백업 및 클라우드 동기화 지원
"""

import os
import json
import shutil
import zipfile
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import glob


@dataclass
class BackupInfo:
    """백업 정보"""
    id: str
    filename: str
    created_at: str
    size: int  # bytes
    file_count: int
    description: str = ""
    checksum: str = ""


@dataclass
class BackupConfig:
    """백업 설정"""
    auto_backup: bool = True
    backup_interval_hours: int = 24
    max_backups: int = 10
    include_logs: bool = False
    include_cache: bool = False
    compress: bool = True


class BackupManager:
    """백업 관리자"""

    # 백업할 파일/폴더 패턴
    BACKUP_PATTERNS = [
        "portfolio.json",
        "watchlist.json",
        "config.yaml",
        "alerts/*.json",
        "notification_history.json",
        "trades/*.json",
        "*.env"
    ]

    # 제외할 패턴
    EXCLUDE_PATTERNS = [
        "*.pyc",
        "__pycache__",
        "*.log",
        "cache/*"
    ]

    def __init__(self, data_dir: str = None, backup_dir: str = None):
        self.data_dir = Path(data_dir or Path.home() / ".notion_portfolio")
        self.backup_dir = Path(backup_dir or self.data_dir / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.config = BackupConfig()
        self._load_config()

    def _load_config(self):
        """설정 로드"""
        config_file = self.data_dir / "backup_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
            except Exception:
                pass

    def _save_config(self):
        """설정 저장"""
        config_file = self.data_dir / "backup_config.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'auto_backup': self.config.auto_backup,
                    'backup_interval_hours': self.config.backup_interval_hours,
                    'max_backups': self.config.max_backups,
                    'include_logs': self.config.include_logs,
                    'include_cache': self.config.include_cache,
                    'compress': self.config.compress
                }, f, indent=2)
        except Exception:
            pass

    def _get_files_to_backup(self) -> List[Path]:
        """백업할 파일 목록"""
        files = []

        for pattern in self.BACKUP_PATTERNS:
            matched = list(self.data_dir.glob(pattern))
            files.extend(matched)

        # 로그 포함
        if self.config.include_logs:
            files.extend(self.data_dir.glob("logs/*.log"))

        # 캐시 포함
        if self.config.include_cache:
            files.extend(self.data_dir.glob("cache/*"))

        # 제외 패턴 적용
        filtered = []
        for f in files:
            exclude = False
            for pattern in self.EXCLUDE_PATTERNS:
                if f.match(pattern):
                    exclude = True
                    break
            if not exclude and f.is_file():
                filtered.append(f)

        return filtered

    def _calculate_checksum(self, filepath: Path) -> str:
        """파일 체크섬 계산"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_backup(self, description: str = "") -> BackupInfo:
        """백업 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp}"

        if self.config.compress:
            backup_filename = f"{backup_id}.zip"
            backup_path = self.backup_dir / backup_filename

            # ZIP 압축
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                files = self._get_files_to_backup()
                for file_path in files:
                    # 상대 경로로 저장
                    arcname = file_path.relative_to(self.data_dir)
                    zf.write(file_path, arcname)

            file_count = len(files)
        else:
            backup_filename = backup_id
            backup_path = self.backup_dir / backup_filename
            backup_path.mkdir(parents=True, exist_ok=True)

            files = self._get_files_to_backup()
            for file_path in files:
                rel_path = file_path.relative_to(self.data_dir)
                dest_path = backup_path / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)

            file_count = len(files)

        # 백업 정보 생성
        backup_info = BackupInfo(
            id=backup_id,
            filename=backup_filename,
            created_at=datetime.now().isoformat(),
            size=backup_path.stat().st_size if backup_path.is_file() else
                 sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()),
            file_count=file_count,
            description=description,
            checksum=self._calculate_checksum(backup_path) if backup_path.is_file() else ""
        )

        # 백업 메타데이터 저장
        self._save_backup_metadata(backup_info)

        # 오래된 백업 정리
        self._cleanup_old_backups()

        return backup_info

    def _save_backup_metadata(self, info: BackupInfo):
        """백업 메타데이터 저장"""
        metadata_file = self.backup_dir / "metadata.json"

        metadata = []
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception:
                pass

        metadata.append({
            'id': info.id,
            'filename': info.filename,
            'created_at': info.created_at,
            'size': info.size,
            'file_count': info.file_count,
            'description': info.description,
            'checksum': info.checksum
        })

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _cleanup_old_backups(self):
        """오래된 백업 정리"""
        backups = self.list_backups()

        if len(backups) > self.config.max_backups:
            # 오래된 순으로 정렬
            backups.sort(key=lambda x: x.created_at)

            # 초과분 삭제
            to_delete = backups[:-self.config.max_backups]
            for backup in to_delete:
                self.delete_backup(backup.id)

    def list_backups(self) -> List[BackupInfo]:
        """백업 목록 조회"""
        metadata_file = self.backup_dir / "metadata.json"

        if not metadata_file.exists():
            return []

        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            backups = []
            for item in data:
                backup_path = self.backup_dir / item['filename']
                if backup_path.exists():
                    backups.append(BackupInfo(**item))

            return sorted(backups, key=lambda x: x.created_at, reverse=True)

        except Exception:
            return []

    def restore_backup(self, backup_id: str,
                       target_dir: str = None) -> bool:
        """백업 복원"""
        backups = {b.id: b for b in self.list_backups()}

        if backup_id not in backups:
            return False

        backup = backups[backup_id]
        backup_path = self.backup_dir / backup.filename
        target = Path(target_dir) if target_dir else self.data_dir

        try:
            if backup_path.suffix == '.zip':
                # ZIP 압축 해제
                with zipfile.ZipFile(backup_path, 'r') as zf:
                    zf.extractall(target)
            else:
                # 폴더 복사
                for file_path in backup_path.rglob('*'):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(backup_path)
                        dest_path = target / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest_path)

            return True

        except Exception as e:
            print(f"백업 복원 실패: {e}")
            return False

    def delete_backup(self, backup_id: str) -> bool:
        """백업 삭제"""
        backups = {b.id: b for b in self.list_backups()}

        if backup_id not in backups:
            return False

        backup = backups[backup_id]
        backup_path = self.backup_dir / backup.filename

        try:
            if backup_path.is_file():
                backup_path.unlink()
            elif backup_path.is_dir():
                shutil.rmtree(backup_path)

            # 메타데이터 업데이트
            metadata_file = self.backup_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                metadata = [m for m in metadata if m['id'] != backup_id]

                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"백업 삭제 실패: {e}")
            return False

    def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """백업 정보 조회"""
        backups = {b.id: b for b in self.list_backups()}
        return backups.get(backup_id)

    def export_backup(self, backup_id: str, dest_path: str) -> bool:
        """백업 내보내기"""
        backups = {b.id: b for b in self.list_backups()}

        if backup_id not in backups:
            return False

        backup = backups[backup_id]
        backup_path = self.backup_dir / backup.filename

        try:
            shutil.copy2(backup_path, dest_path)
            return True
        except Exception as e:
            print(f"백업 내보내기 실패: {e}")
            return False

    def import_backup(self, source_path: str) -> Optional[BackupInfo]:
        """백업 가져오기"""
        source = Path(source_path)

        if not source.exists():
            return None

        try:
            # 새 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"backup_imported_{timestamp}"

            if source.suffix == '.zip':
                dest_filename = f"{backup_id}.zip"
            else:
                dest_filename = backup_id

            dest_path = self.backup_dir / dest_filename
            shutil.copy2(source, dest_path)

            # ZIP 파일인 경우 파일 수 계산
            if dest_path.suffix == '.zip':
                with zipfile.ZipFile(dest_path, 'r') as zf:
                    file_count = len(zf.namelist())
            else:
                file_count = sum(1 for _ in dest_path.rglob('*') if _.is_file())

            backup_info = BackupInfo(
                id=backup_id,
                filename=dest_filename,
                created_at=datetime.now().isoformat(),
                size=dest_path.stat().st_size,
                file_count=file_count,
                description="가져온 백업",
                checksum=self._calculate_checksum(dest_path) if dest_path.is_file() else ""
            )

            self._save_backup_metadata(backup_info)
            return backup_info

        except Exception as e:
            print(f"백업 가져오기 실패: {e}")
            return None

    def check_backup_needed(self) -> bool:
        """백업 필요 여부 확인"""
        if not self.config.auto_backup:
            return False

        backups = self.list_backups()

        if not backups:
            return True

        last_backup = backups[0]  # 최신 백업
        last_time = datetime.fromisoformat(last_backup.created_at)
        hours_since = (datetime.now() - last_time).total_seconds() / 3600

        return hours_since >= self.config.backup_interval_hours

    def auto_backup_if_needed(self) -> Optional[BackupInfo]:
        """필요시 자동 백업"""
        if self.check_backup_needed():
            return self.create_backup("자동 백업")
        return None

    def get_storage_usage(self) -> Dict[str, Any]:
        """저장소 사용량"""
        total_size = sum(f.stat().st_size for f in self.backup_dir.rglob('*') if f.is_file())
        backup_count = len(self.list_backups())

        return {
            "total_size": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "backup_count": backup_count,
            "max_backups": self.config.max_backups,
            "backup_dir": str(self.backup_dir)
        }


# 싱글톤 인스턴스
backup_manager = BackupManager()


def create_backup(description: str = "") -> BackupInfo:
    """백업 생성"""
    return backup_manager.create_backup(description)


def restore_backup(backup_id: str) -> bool:
    """백업 복원"""
    return backup_manager.restore_backup(backup_id)


def list_backups() -> List[BackupInfo]:
    """백업 목록"""
    return backup_manager.list_backups()


def auto_backup() -> Optional[BackupInfo]:
    """자동 백업"""
    return backup_manager.auto_backup_if_needed()
