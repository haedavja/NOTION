"""
워치리스트 컴포넌트
관심 종목 저장 및 관리
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

# 워치리스트 저장 경로
WATCHLIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'watchlists')


@dataclass
class WatchlistItem:
    """워치리스트 항목"""
    code: str
    name: str
    added_date: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    memo: str = ""
    alert_enabled: bool = False
    buy_price: Optional[float] = None


@dataclass
class Watchlist:
    """워치리스트"""
    name: str
    items: List[WatchlistItem]
    created_date: str
    modified_date: str


def ensure_watchlist_dir():
    """워치리스트 디렉토리 확인"""
    if not os.path.exists(WATCHLIST_DIR):
        os.makedirs(WATCHLIST_DIR, exist_ok=True)


def get_watchlist_path(name: str) -> str:
    """워치리스트 파일 경로"""
    return os.path.join(WATCHLIST_DIR, f"{name}.json")


def save_watchlist(watchlist: Watchlist) -> bool:
    """워치리스트 저장"""
    try:
        ensure_watchlist_dir()
        path = get_watchlist_path(watchlist.name)

        # 수정 시간 업데이트
        watchlist.modified_date = datetime.now().isoformat()

        data = {
            'name': watchlist.name,
            'items': [asdict(item) for item in watchlist.items],
            'created_date': watchlist.created_date,
            'modified_date': watchlist.modified_date
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"워치리스트 저장 실패: {e}")
        return False


def load_watchlist(name: str) -> Optional[Watchlist]:
    """워치리스트 불러오기"""
    try:
        path = get_watchlist_path(name)
        if not os.path.exists(path):
            return None

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        items = [WatchlistItem(**item) for item in data.get('items', [])]

        return Watchlist(
            name=data['name'],
            items=items,
            created_date=data.get('created_date', ''),
            modified_date=data.get('modified_date', '')
        )
    except Exception as e:
        logger.error(f"워치리스트 불러오기 실패: {e}")
        return None


def delete_watchlist(name: str) -> bool:
    """워치리스트 삭제"""
    try:
        path = get_watchlist_path(name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    except Exception as e:
        logger.error(f"워치리스트 삭제 실패: {e}")
        return False


def list_watchlists() -> List[str]:
    """모든 워치리스트 목록"""
    try:
        ensure_watchlist_dir()
        files = os.listdir(WATCHLIST_DIR)
        return [f.replace('.json', '') for f in files if f.endswith('.json')]
    except Exception:
        return []


def get_default_watchlist() -> Watchlist:
    """기본 워치리스트 생성"""
    now = datetime.now().isoformat()
    return Watchlist(
        name='기본',
        items=[],
        created_date=now,
        modified_date=now
    )


def get_session_watchlist() -> Watchlist:
    """세션의 현재 워치리스트 가져오기"""
    if 'current_watchlist' not in st.session_state:
        # 저장된 기본 워치리스트 로드 시도
        saved = load_watchlist('기본')
        if saved:
            st.session_state['current_watchlist'] = saved
        else:
            st.session_state['current_watchlist'] = get_default_watchlist()

    return st.session_state['current_watchlist']


def add_to_watchlist(
    code: str,
    name: str,
    target_price: float = None,
    stop_loss: float = None,
    memo: str = "",
    buy_price: float = None
) -> bool:
    """워치리스트에 종목 추가"""
    watchlist = get_session_watchlist()

    # 중복 체크
    if any(item.code == code for item in watchlist.items):
        return False

    item = WatchlistItem(
        code=code,
        name=name,
        added_date=datetime.now().isoformat(),
        target_price=target_price,
        stop_loss=stop_loss,
        memo=memo,
        buy_price=buy_price
    )

    watchlist.items.append(item)
    save_watchlist(watchlist)
    return True


def remove_from_watchlist(code: str) -> bool:
    """워치리스트에서 종목 제거"""
    watchlist = get_session_watchlist()
    original_len = len(watchlist.items)
    watchlist.items = [item for item in watchlist.items if item.code != code]

    if len(watchlist.items) < original_len:
        save_watchlist(watchlist)
        return True
    return False


def update_watchlist_item(code: str, **kwargs) -> bool:
    """워치리스트 항목 업데이트"""
    watchlist = get_session_watchlist()

    for item in watchlist.items:
        if item.code == code:
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            save_watchlist(watchlist)
            return True
    return False


def is_in_watchlist(code: str) -> bool:
    """워치리스트에 있는지 확인"""
    watchlist = get_session_watchlist()
    return any(item.code == code for item in watchlist.items)


def render_add_to_watchlist_button(code: str, name: str, key: str = None):
    """워치리스트 추가 버튼 렌더링"""
    button_key = key or f"watchlist_btn_{code}"

    if is_in_watchlist(code):
        if st.button("⭐ 관심 해제", key=button_key, type="secondary"):
            if remove_from_watchlist(code):
                st.success(f"{name}을(를) 관심 종목에서 제거했습니다.")
                st.rerun()
    else:
        if st.button("☆ 관심 등록", key=button_key, type="primary"):
            if add_to_watchlist(code, name):
                st.success(f"{name}을(를) 관심 종목에 추가했습니다!")
                st.rerun()
            else:
                st.warning("이미 관심 종목에 있습니다.")


def render_watchlist_manager():
    """워치리스트 관리 UI"""
    st.subheader("⭐ 관심 종목 관리")

    watchlist = get_session_watchlist()

    # 워치리스트 선택/생성
    col1, col2 = st.columns([3, 1])

    with col1:
        available_lists = list_watchlists() or ['기본']
        if watchlist.name not in available_lists:
            available_lists.append(watchlist.name)

        selected = st.selectbox(
            "워치리스트 선택",
            options=available_lists,
            index=available_lists.index(watchlist.name) if watchlist.name in available_lists else 0
        )

        if selected != watchlist.name:
            loaded = load_watchlist(selected)
            if loaded:
                st.session_state['current_watchlist'] = loaded
                st.rerun()

    with col2:
        if st.button("➕ 새 리스트"):
            new_name = f"워치리스트_{len(available_lists) + 1}"
            new_list = Watchlist(
                name=new_name,
                items=[],
                created_date=datetime.now().isoformat(),
                modified_date=datetime.now().isoformat()
            )
            save_watchlist(new_list)
            st.session_state['current_watchlist'] = new_list
            st.rerun()

    st.divider()

    # 종목 목록
    if not watchlist.items:
        st.info("👀 관심 종목이 없습니다. 종목 분석 후 '관심 등록' 버튼을 눌러 추가하세요!")
        return

    # 테이블 형태로 표시
    for i, item in enumerate(watchlist.items):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 1])

            with col1:
                st.markdown(f"**{item.name}**")
                st.caption(f"{item.code}")

            with col2:
                if item.target_price:
                    st.metric("목표가", f"{item.target_price:,.0f}원")
                else:
                    st.caption("목표가 미설정")

            with col3:
                if item.stop_loss:
                    st.metric("손절가", f"{item.stop_loss:,.0f}원")
                else:
                    st.caption("손절가 미설정")

            with col4:
                if item.buy_price:
                    st.metric("매수가", f"{item.buy_price:,.0f}원")
                else:
                    st.caption("매수가 미설정")

            with col5:
                if st.button("❌", key=f"remove_{item.code}_{i}", help="삭제"):
                    if remove_from_watchlist(item.code):
                        st.rerun()

            # 메모 표시
            if item.memo:
                st.caption(f"📝 {item.memo}")

            st.divider()

    # 일괄 작업
    st.markdown("### 📋 일괄 작업")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤 내보내기 (JSON)", use_container_width=True):
            export_data = {
                'name': watchlist.name,
                'exported_date': datetime.now().isoformat(),
                'items': [asdict(item) for item in watchlist.items]
            }
            st.download_button(
                "💾 다운로드",
                data=json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"watchlist_{watchlist.name}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

    with col2:
        uploaded = st.file_uploader("📥 불러오기", type=['json'], key="watchlist_import")
        if uploaded:
            try:
                data = json.load(uploaded)
                imported_items = [WatchlistItem(**item) for item in data.get('items', [])]

                for item in imported_items:
                    if not is_in_watchlist(item.code):
                        watchlist.items.append(item)

                save_watchlist(watchlist)
                st.success(f"{len(imported_items)}개 종목을 가져왔습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"가져오기 실패: {e}")

    with col3:
        if st.button("🗑️ 전체 삭제", use_container_width=True, type="secondary"):
            if st.session_state.get('confirm_delete_all'):
                watchlist.items = []
                save_watchlist(watchlist)
                st.session_state['confirm_delete_all'] = False
                st.rerun()
            else:
                st.session_state['confirm_delete_all'] = True
                st.warning("한번 더 클릭하면 전체 삭제됩니다.")


def render_watchlist_quick_view():
    """워치리스트 빠른 보기 (사이드바용)"""
    watchlist = get_session_watchlist()

    with st.expander(f"⭐ 관심 종목 ({len(watchlist.items)})", expanded=False):
        if not watchlist.items:
            st.caption("관심 종목이 없습니다.")
            return

        for item in watchlist.items[:5]:  # 최대 5개만 표시
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"**{item.name}** ({item.code})")
            with col2:
                if item.target_price:
                    st.caption(f"목표: {item.target_price:,.0f}")

        if len(watchlist.items) > 5:
            st.caption(f"외 {len(watchlist.items) - 5}개...")


def render_watchlist_item_editor(code: str, name: str):
    """워치리스트 항목 편집기"""
    watchlist = get_session_watchlist()
    item = next((i for i in watchlist.items if i.code == code), None)

    if not item:
        st.warning("워치리스트에 없는 종목입니다.")
        return

    st.markdown(f"### ✏️ {name} 설정")

    col1, col2 = st.columns(2)

    with col1:
        target_price = st.number_input(
            "목표가",
            value=item.target_price or 0,
            min_value=0,
            step=1000,
            format="%d",
            key=f"target_{code}"
        )

        buy_price = st.number_input(
            "매수가",
            value=item.buy_price or 0,
            min_value=0,
            step=1000,
            format="%d",
            key=f"buy_{code}"
        )

    with col2:
        stop_loss = st.number_input(
            "손절가",
            value=item.stop_loss or 0,
            min_value=0,
            step=1000,
            format="%d",
            key=f"stop_{code}"
        )

        alert_enabled = st.checkbox(
            "알림 받기",
            value=item.alert_enabled,
            key=f"alert_{code}"
        )

    memo = st.text_area(
        "메모",
        value=item.memo,
        placeholder="투자 아이디어, 매수 이유 등을 기록하세요...",
        key=f"memo_{code}"
    )

    if st.button("💾 저장", key=f"save_{code}", use_container_width=True):
        update_watchlist_item(
            code,
            target_price=target_price if target_price > 0 else None,
            stop_loss=stop_loss if stop_loss > 0 else None,
            buy_price=buy_price if buy_price > 0 else None,
            memo=memo,
            alert_enabled=alert_enabled
        )
        st.success("저장되었습니다!")


def get_watchlist_codes() -> List[str]:
    """워치리스트의 모든 종목 코드"""
    watchlist = get_session_watchlist()
    return [item.code for item in watchlist.items]


def get_alerts() -> List[Dict[str, Any]]:
    """알림이 설정된 종목 목록"""
    watchlist = get_session_watchlist()
    alerts = []

    for item in watchlist.items:
        if item.alert_enabled and (item.target_price or item.stop_loss):
            alerts.append({
                'code': item.code,
                'name': item.name,
                'target_price': item.target_price,
                'stop_loss': item.stop_loss
            })

    return alerts
