import streamlit as st


def inject_mobile_styles() -> None:
    st.markdown(
        """
        <style>
        /* Touch-friendly inputs (prevents iOS zoom on focus) */
        input, textarea, select {
            font-size: 16px !important;
        }

        /* Scrollable horizontal tab bars on narrow screens */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            overflow-y: hidden;
            flex-wrap: nowrap;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none;
        }
        .stTabs [data-baseweb="tab"] {
            min-height: 44px;
            white-space: nowrap;
            flex-shrink: 0;
        }

        /* Sidebar page navigation (st.navigation) */
        [data-testid="stSidebarNav"] a {
            min-height: 44px;
            display: flex;
            align-items: center;
        }
        [data-testid="stSidebarNav"] ul {
            gap: 0.25rem;
        }
        [data-testid="stSidebarNav"] a[href*="logout"] {
            font-size: 0.82rem !important;
            opacity: 0.8;
            min-height: 34px !important;
        }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            margin-bottom: 0.35rem;
        }

        /* Sidebar vertical nav tabs (fallback custom nav) */
        [data-testid="stSidebar"] .sidebar-nav-tabs {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            margin: 0.25rem 0 0.75rem;
        }
        [data-testid="stSidebar"] .sidebar-nav-tabs .stButton > button {
            width: 100%;
            min-height: 44px;
            justify-content: flex-start;
            padding: 0.55rem 0.85rem;
            border-radius: 8px;
            font-weight: 500;
            transition: background 0.15s ease, border-color 0.15s ease;
        }
        [data-testid="stSidebar"] .sidebar-nav-tabs .stButton > button[kind="secondary"] {
            background: transparent;
            border: 1px solid transparent;
            color: inherit;
        }
        [data-testid="stSidebar"] .sidebar-nav-tabs .stButton > button[kind="secondary"]:hover {
            background: rgba(151, 166, 195, 0.15);
            border-color: rgba(151, 166, 195, 0.25);
        }
        [data-testid="stSidebar"] .sidebar-nav-tabs .stButton > button[kind="primary"] {
            border-left: 3px solid #ff4b4b;
            font-weight: 700;
        }

        /* Block headers wrap on small screens */
        .block-header-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            flex-wrap: wrap;
        }
        .block-header-title {
            font-weight: 700;
            flex: 1 1 12rem;
            min-width: 0;
            word-break: break-word;
        }
        .block-header-badge {
            font-weight: 700;
            font-size: 0.85rem;
            white-space: nowrap;
            flex-shrink: 0;
        }

        /* Legend wraps on mobile */
        .block-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 1rem;
            margin: 0 0 0.9rem;
        }

        /* Stat cards: 2-up on tablet, 1-up on phone */
        @media (max-width: 900px) {
            .stat-value {
                font-size: 1.6rem !important;
            }
        }

        @media (max-width: 768px) {
            /* Stack column layouts vertically — but not block ribbons */
            div[data-testid="stHorizontalBlock"]:not(:has(.block-ribbon-marker)):not(:has(.plan-date-nav-wrap-marker)):not(:has(.todo-ribbon-marker)):not(:has(.todo-date-nav-wrap-marker)) {
                flex-direction: column !important;
                gap: 0.65rem !important;
                align-items: stretch !important;
            }
            div[data-testid="stHorizontalBlock"]:not(:has(.block-ribbon-marker)):not(:has(.plan-date-nav-wrap-marker)):not(:has(.todo-ribbon-marker)):not(:has(.todo-date-nav-wrap-marker)) > div[data-testid="column"] {
                width: 100% !important;
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }

            /* Comfortable page padding */
            .block-container {
                padding-left: 0.85rem !important;
                padding-right: 0.85rem !important;
            }

            /* Slightly smaller titles */
            h1 {
                font-size: 1.55rem !important;
            }
            h2, h3 {
                font-size: 1.15rem !important;
            }

            .stat-value {
                font-size: 1.45rem !important;
            }

            .achievement-value {
                font-size: 1.55rem !important;
            }
        }

        @media (max-width: 480px) {
            [data-testid="stSidebar"] {
                min-width: min(18rem, 85vw);
            }
        }

        .planner-tag-pill {
            display: inline-block;
            color: #FFFFFF;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            margin-right: 0.35rem;
            vertical-align: middle;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.25);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
