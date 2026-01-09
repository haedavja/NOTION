"""
키보드 단축키 지원
파워 유저를 위한 키보드 네비게이션
"""

import streamlit as st
import streamlit.components.v1 as components


def inject_keyboard_shortcuts():
    """키보드 단축키 JavaScript 삽입"""

    shortcut_js = """
    <script>
    // NOTION 포트폴리오 키보드 단축키
    (function() {
        // 이미 등록되어 있으면 스킵
        if (window.notionShortcutsRegistered) return;
        window.notionShortcutsRegistered = true;

        // 단축키 도움말 표시 여부
        let helpVisible = false;

        // 단축키 목록
        const shortcuts = {
            'h': { desc: '도움말 토글', action: toggleHelp },
            '1': { desc: '종합 예측 탭', action: () => clickTab(0) },
            '2': { desc: '거시경제 탭', action: () => clickTab(1) },
            '3': { desc: '자금흐름 탭', action: () => clickTab(2) },
            '4': { desc: '센티먼트 탭', action: () => clickTab(3) },
            '5': { desc: '기술적 분석 탭', action: () => clickTab(4) },
            '6': { desc: '포트폴리오 탭', action: () => clickTab(5) },
            '7': { desc: '백테스트 탭', action: () => clickTab(6) },
            '8': { desc: 'AI 분석 탭', action: () => clickTab(7) },
            '9': { desc: '한국 주식 탭', action: () => clickTab(8) },
            '0': { desc: '고급 기능 탭', action: () => clickTab(9) },
            'r': { desc: '새로고침', action: () => window.location.reload() },
            's': { desc: '사이드바 토글', action: toggleSidebar },
            '/': { desc: '검색 포커스', action: focusSearch },
            'Escape': { desc: '닫기/취소', action: closeModals }
        };

        // 탭 클릭
        function clickTab(index) {
            const tabs = document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs[index]) {
                tabs[index].click();
            }
        }

        // 사이드바 토글
        function toggleSidebar() {
            const sidebar = document.querySelector('[data-testid="stSidebar"]');
            const button = document.querySelector('[data-testid="collapsedControl"]');
            if (button) button.click();
        }

        // 검색 포커스
        function focusSearch() {
            const inputs = document.querySelectorAll('input[type="text"]');
            for (let input of inputs) {
                if (input.placeholder && input.placeholder.includes('검색')) {
                    input.focus();
                    return;
                }
            }
            // 첫 번째 입력 필드에 포커스
            if (inputs[0]) inputs[0].focus();
        }

        // 모달 닫기
        function closeModals() {
            const closeButtons = document.querySelectorAll('[aria-label="Close"]');
            closeButtons.forEach(btn => btn.click());

            // expander 닫기
            const expanders = document.querySelectorAll('[data-testid="stExpander"] summary');
            expanders.forEach(exp => {
                if (exp.getAttribute('aria-expanded') === 'true') {
                    exp.click();
                }
            });
        }

        // 도움말 토글
        function toggleHelp() {
            let helpDiv = document.getElementById('notion-shortcuts-help');

            if (helpDiv) {
                helpDiv.remove();
                helpVisible = false;
                return;
            }

            // 도움말 생성
            helpDiv = document.createElement('div');
            helpDiv.id = 'notion-shortcuts-help';
            helpDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                z-index: 10000;
                max-width: 500px;
                max-height: 80vh;
                overflow-y: auto;
            `;

            let html = `
                <h3 style="margin-top:0; color:#1f77b4;">⌨️ 키보드 단축키</h3>
                <table style="width:100%; border-collapse:collapse;">
                    <tr style="background:#f0f2f6;">
                        <th style="padding:8px; text-align:left;">키</th>
                        <th style="padding:8px; text-align:left;">기능</th>
                    </tr>
            `;

            for (const [key, data] of Object.entries(shortcuts)) {
                html += `
                    <tr style="border-bottom:1px solid #eee;">
                        <td style="padding:8px;"><kbd style="background:#eee;padding:2px 6px;border-radius:3px;">${key}</kbd></td>
                        <td style="padding:8px;">${data.desc}</td>
                    </tr>
                `;
            }

            html += `
                </table>
                <p style="margin-top:16px; color:#666; font-size:12px;">
                    💡 Tip: 입력 필드에서는 단축키가 비활성화됩니다.
                </p>
                <button onclick="this.parentElement.remove()" style="
                    margin-top:12px;
                    padding:8px 16px;
                    background:#1f77b4;
                    color:white;
                    border:none;
                    border-radius:6px;
                    cursor:pointer;
                ">닫기 (H 또는 ESC)</button>
            `;

            helpDiv.innerHTML = html;
            document.body.appendChild(helpDiv);
            helpVisible = true;
        }

        // 키 이벤트 리스너
        document.addEventListener('keydown', function(e) {
            // 입력 필드에서는 무시
            if (e.target.tagName === 'INPUT' ||
                e.target.tagName === 'TEXTAREA' ||
                e.target.isContentEditable) {
                return;
            }

            // Ctrl/Cmd 조합은 무시 (브라우저 단축키)
            if (e.ctrlKey || e.metaKey) return;

            const key = e.key;
            const shortcut = shortcuts[key];

            if (shortcut) {
                e.preventDefault();
                shortcut.action();
            }
        });

        // 초기화 메시지
        console.log('NOTION 키보드 단축키 활성화됨. H키로 도움말 확인');
    })();
    </script>

    <style>
    /* 키보드 단축키 힌트 스타일 */
    kbd {
        background-color: #eee;
        border-radius: 3px;
        border: 1px solid #b4b4b4;
        box-shadow: 0 1px 1px rgba(0,0,0,.2);
        color: #333;
        display: inline-block;
        font-size: .85em;
        font-weight: 700;
        line-height: 1;
        padding: 2px 4px;
        white-space: nowrap;
    }
    </style>
    """

    components.html(shortcut_js, height=0)


def render_shortcuts_help():
    """단축키 도움말 표시"""
    st.markdown("""
    ### ⌨️ 키보드 단축키

    | 키 | 기능 |
    |---|---|
    | `H` | 도움말 토글 |
    | `1-9, 0` | 탭 전환 |
    | `R` | 페이지 새로고침 |
    | `S` | 사이드바 토글 |
    | `/` | 검색 포커스 |
    | `ESC` | 닫기/취소 |

    💡 **Tip**: 입력 필드에서는 단축키가 비활성화됩니다.
    """)


def add_shortcut_indicator():
    """단축키 표시 아이콘"""
    st.sidebar.markdown("""
    ---
    <div style="text-align:center; color:#666; font-size:12px;">
        ⌨️ <kbd>H</kbd> 키로 단축키 확인
    </div>
    """, unsafe_allow_html=True)
