"""
사용자 인증 모듈
streamlit-authenticator 기반 또는 간단한 비밀번호 인증
"""

import streamlit as st
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path


class SimpleAuth:
    """간단한 비밀번호 인증 (streamlit-authenticator 없을 때 폴백)"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.expanduser("~"), ".notion_portfolio", "auth.json")

        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._load_config()

    def _load_config(self):
        """설정 로드"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            # 기본 설정 (비밀번호: admin)
            self.config = {
                'enabled': False,
                'users': {
                    'admin': {
                        'password_hash': self._hash_password('admin'),
                        'name': '관리자',
                        'created_at': datetime.now().isoformat()
                    }
                }
            }
            self._save_config()

    def _save_config(self):
        """설정 저장"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _hash_password(self, password: str) -> str:
        """비밀번호 해시"""
        return hashlib.sha256(password.encode()).hexdigest()

    def is_enabled(self) -> bool:
        """인증 활성화 여부"""
        return self.config.get('enabled', False)

    def enable(self):
        """인증 활성화"""
        self.config['enabled'] = True
        self._save_config()

    def disable(self):
        """인증 비활성화"""
        self.config['enabled'] = False
        self._save_config()

    def authenticate(self, username: str, password: str) -> bool:
        """인증"""
        if username not in self.config['users']:
            return False

        user = self.config['users'][username]
        return user['password_hash'] == self._hash_password(password)

    def add_user(self, username: str, password: str, name: str = None):
        """사용자 추가"""
        self.config['users'][username] = {
            'password_hash': self._hash_password(password),
            'name': name or username,
            'created_at': datetime.now().isoformat()
        }
        self._save_config()

    def change_password(self, username: str, new_password: str) -> bool:
        """비밀번호 변경"""
        if username not in self.config['users']:
            return False

        self.config['users'][username]['password_hash'] = self._hash_password(new_password)
        self._save_config()
        return True

    def get_user_name(self, username: str) -> str:
        """사용자 이름 가져오기"""
        if username in self.config['users']:
            return self.config['users'][username].get('name', username)
        return username


# 전역 인스턴스
auth = SimpleAuth()


def render_login_page() -> bool:
    """로그인 페이지 렌더링, 인증 성공 시 True 반환"""
    if not auth.is_enabled():
        return True

    # 이미 로그인됨
    if st.session_state.get('authenticated'):
        return True

    st.title("🔐 로그인")

    with st.form("login_form"):
        username = st.text_input("사용자명")
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("로그인")

        if submit:
            if auth.authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_name = auth.get_user_name(username)
                st.success(f"환영합니다, {st.session_state.user_name}님!")
                st.rerun()
            else:
                st.error("사용자명 또는 비밀번호가 잘못되었습니다.")

    st.info("💡 기본 계정: admin / admin")
    return False


def render_logout_button():
    """로그아웃 버튼"""
    if st.session_state.get('authenticated'):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"👤 {st.session_state.get('user_name', '사용자')}")
        with col2:
            if st.button("로그아웃", key="logout_btn"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.user_name = None
                st.rerun()


def render_auth_settings():
    """인증 설정 UI"""
    st.subheader("🔐 인증 설정")

    enabled = st.checkbox("인증 활성화", value=auth.is_enabled())
    if enabled != auth.is_enabled():
        if enabled:
            auth.enable()
            st.success("인증이 활성화되었습니다.")
        else:
            auth.disable()
            st.warning("인증이 비활성화되었습니다.")

    if auth.is_enabled():
        st.divider()
        st.markdown("#### 비밀번호 변경")

        with st.form("change_password_form"):
            current = st.text_input("현재 비밀번호", type="password")
            new_pw = st.text_input("새 비밀번호", type="password")
            confirm = st.text_input("비밀번호 확인", type="password")

            if st.form_submit_button("변경"):
                username = st.session_state.get('username', 'admin')
                if not auth.authenticate(username, current):
                    st.error("현재 비밀번호가 잘못되었습니다.")
                elif new_pw != confirm:
                    st.error("새 비밀번호가 일치하지 않습니다.")
                elif len(new_pw) < 4:
                    st.error("비밀번호는 4자 이상이어야 합니다.")
                else:
                    auth.change_password(username, new_pw)
                    st.success("비밀번호가 변경되었습니다.")


def require_auth(func):
    """인증 필요 데코레이터"""
    def wrapper(*args, **kwargs):
        if not auth.is_enabled() or st.session_state.get('authenticated'):
            return func(*args, **kwargs)
        else:
            render_login_page()
            return None
    return wrapper
