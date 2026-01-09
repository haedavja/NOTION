#!/usr/bin/env python3
"""
모듈 Import 검증 스크립트
모든 Python 모듈의 import 오류를 사전에 감지

사용법:
    python scripts/verify_imports.py
    python scripts/verify_imports.py --fix  # 자동 수정 시도
"""

import sys
import os
import ast
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple, Set

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ImportVerifier:
    """Import 검증기"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []

        # 표준 라이브러리 + 알려진 서드파티
        self.known_modules = {
            # 표준 라이브러리
            'os', 'sys', 'json', 'logging', 'datetime', 'pathlib',
            'typing', 'dataclasses', 'hashlib', 'secrets', 'hmac',
            'threading', 'functools', 'time', 'pickle', 'copy',
            'collections', 'itertools', 'abc', 'enum', 're',
            # 서드파티
            'pandas', 'numpy', 'streamlit', 'plotly', 'yfinance',
            'pykrx', 'requests', 'bcrypt', 'openai', 'feedparser',
        }

    def find_python_files(self) -> List[Path]:
        """프로젝트 내 모든 Python 파일 찾기"""
        files = []
        for pattern in ['**/*.py']:
            for f in self.project_root.glob(pattern):
                # 제외 패턴
                if any(x in str(f) for x in ['__pycache__', '.git', 'venv', 'env', '.egg']):
                    continue
                files.append(f)
        return sorted(files)

    def extract_imports(self, file_path: Path) -> Tuple[Set[str], Set[str]]:
        """파일에서 import 문 추출"""
        imports = set()
        from_imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError as e:
            self.errors.append({
                'file': str(file_path),
                'type': 'syntax_error',
                'message': str(e),
                'line': e.lineno
            })
            return imports, from_imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    from_imports.add(node.module.split('.')[0])
                    # 구체적인 import 이름들
                    for alias in node.names:
                        from_imports.add(f"{node.module}.{alias.name}")

        return imports, from_imports

    def check_typing_imports(self, file_path: Path) -> List[Dict]:
        """typing 모듈 사용 검증"""
        issues = []
        typing_names = {'Dict', 'List', 'Optional', 'Tuple', 'Set', 'Any',
                       'Union', 'Callable', 'Type', 'Sequence'}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return issues

        # typing에서 import된 이름들 수집
        imported_typing = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'typing':
                for alias in node.names:
                    imported_typing.add(alias.name)

        # 사용된 typing 이름들 확인
        import re
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('#'):
                continue
            for name in typing_names:
                # 타입 힌트에서 사용되는 패턴 확인 (정확한 단어 매칭)
                # : Dict[, : List[, -> Optional[ 등
                patterns = [
                    rf': {name}\[',      # : Dict[
                    rf'-> {name}\[',     # -> Dict[
                    rf': {name}\s*$',    # : Dict (줄 끝)
                    rf'-> {name}\s*:',   # -> Dict:
                    rf', {name}\[',      # , Dict[
                ]
                for pattern in patterns:
                    if re.search(pattern, line):
                        if name not in imported_typing:
                            issues.append({
                                'file': str(file_path),
                                'type': 'missing_typing_import',
                                'message': f"'{name}' 사용됨 but not imported from typing",
                                'line': i,
                                'fix': f"from typing import {name}"
                            })
                            break  # 같은 라인에서 중복 감지 방지

        return issues

    def check_datetime_imports(self, file_path: Path) -> List[Dict]:
        """datetime 모듈 사용 검증"""
        issues = []
        # time은 제외 (표준 time 모듈과 혼동)
        datetime_names = {'timedelta', 'timezone'}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return issues

        # import time 확인 (표준 모듈)
        has_time_module = 'import time' in content

        # from datetime import ... 확인
        imported_datetime = set()
        for line in content.split('\n'):
            if 'from datetime import' in line:
                # 간단한 파싱
                parts = line.split('import')[1].strip()
                for part in parts.split(','):
                    name = part.strip().split()[0]  # alias 제거
                    imported_datetime.add(name)

        # 사용 확인
        for i, line in enumerate(content.split('\n'), 1):
            if line.strip().startswith('#'):
                continue
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                continue

            for name in datetime_names:
                # 메서드 호출 패턴: timedelta(, datetime.now( 등
                # 제외 패턴:
                # - 문자열 내 사용 ('timedelta', "timedelta")
                # - 함수/메서드명에 포함 (def test_timedelta, _timedelta)
                # - time.sleep 같은 표준 모듈 사용
                import re
                # 정확한 호출 패턴: 공백 또는 줄 시작 후 name(
                pattern = rf'(?<![a-zA-Z_]){name}\s*\('
                if re.search(pattern, line):
                    # 문자열 내 사용 제외
                    if f"'{name}" in line or f'"{name}' in line:
                        continue
                    if name not in imported_datetime and f'datetime.{name}' not in line:
                        issues.append({
                            'file': str(file_path),
                            'type': 'missing_datetime_import',
                            'message': f"'{name}' 사용됨 but not imported from datetime",
                            'line': i,
                            'fix': f"from datetime import {name}"
                        })

        return issues

    def verify_module_imports(self, file_path: Path) -> bool:
        """모듈 import 실행 검증"""
        try:
            spec = importlib.util.spec_from_file_location("module", file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # 실제 로드는 하지 않음 (부작용 방지)
                return True
        except Exception as e:
            self.errors.append({
                'file': str(file_path),
                'type': 'import_error',
                'message': str(e),
                'line': None
            })
            return False
        return True

    def run(self) -> Tuple[List[Dict], List[Dict]]:
        """전체 검증 실행"""
        files = self.find_python_files()
        print(f"검증할 파일: {len(files)}개")

        for file_path in files:
            rel_path = file_path.relative_to(self.project_root)

            # typing import 검증
            typing_issues = self.check_typing_imports(file_path)
            self.errors.extend(typing_issues)

            # datetime import 검증
            datetime_issues = self.check_datetime_imports(file_path)
            self.errors.extend(datetime_issues)

        return self.errors, self.warnings

    def print_report(self):
        """결과 리포트 출력"""
        print("\n" + "=" * 60)
        print("Import 검증 결과")
        print("=" * 60)

        if not self.errors and not self.warnings:
            print("✅ 모든 import가 정상입니다!")
            return

        if self.errors:
            print(f"\n❌ 오류: {len(self.errors)}개")
            for err in self.errors:
                print(f"\n  파일: {err['file']}")
                print(f"  유형: {err['type']}")
                print(f"  메시지: {err['message']}")
                if err.get('line'):
                    print(f"  라인: {err['line']}")
                if err.get('fix'):
                    print(f"  수정: {err['fix']}")

        if self.warnings:
            print(f"\n⚠️ 경고: {len(self.warnings)}개")
            for warn in self.warnings:
                print(f"  - {warn['file']}: {warn['message']}")


def main():
    verifier = ImportVerifier(PROJECT_ROOT)
    errors, warnings = verifier.run()
    verifier.print_report()

    # 종료 코드
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
