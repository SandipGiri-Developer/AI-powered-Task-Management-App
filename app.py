import streamlit as st
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager

from modules.database import check_all_deadlines, get_db
from modules.manager import render_manager_dashboard
from modules.employee import render_employee_dashboard

cookies = EncryptedCookieManager(prefix="task_app", password="secret_key_123")
if not cookies.ready():
    st.stop()



st.set_page_config(page_title="Task Management System", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

check_all_deadlines(supabase)


if 'checked' not in st.session_state:
    check_all_deadlines(supabase)
    st.session_state['checked'] = True

if 'user' not in st.session_state and 'user' in cookies:
    uid = cookies['user']
    res = supabase.table('users').select("*").eq('id', uid).execute()
    if res.data:
        st.session_state['user'] = res.data[0]

if "user" not in st.session_state:

    st.markdown(
        """
        <style>
        .center-box {
            max-width: 420px;
            margin: auto;
            padding: 2rem;
            border-radius: 12px;
            background: #111;
            box-shadow: 0 0 15px rgba(0,0,0,0.4);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="center-box">', unsafe_allow_html=True)

    st.title("Login / Signup")

    mode = st.radio(
        "Mode",
        ["Login", "Sign Up"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if mode == "Sign Up":
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["manager", "employee"])

        if st.button("Register", use_container_width=True):
            try:
                supabase.table("users").insert({
                    "email": email,
                    "full_name": name,
                    "role": role
                }).execute()

                st.success("Registered. Switch to login.")

            except Exception as e:
                st.error(str(e))

    else:
        email = st.text_input("Email")

        if st.button("Login", use_container_width=True):
            resp = supabase.table("users").select("*").eq("email", email).execute()

            if resp.data:
                st.session_state["user"] = resp.data[0]
                cookies["user"] = str(resp.data[0]["id"])
                cookies.save()
                st.rerun()
            else:
                st.error("User not found")

    st.markdown("</div>", unsafe_allow_html=True)


else:
    user = st.session_state['user']
    
    with st.sidebar:
        if "user" in st.session_state:
            user = st.session_state["user"]

            st.write(f"**{user['full_name']}** ({user['role']})")

            if st.button("Logout", use_container_width=True):
                st.session_state.pop("user", None)
                cookies.pop("user", None)
                cookies.save()
                st.rerun()

        
        st.divider()
        st.subheader("🔔 Notifications")
        
        msgs_resp = supabase.table('messages').select("*").eq('recipient_id', user['id']).order('created_at', desc=True).execute()
        msgs = msgs_resp.data or []
        
        if msgs:
            for m in msgs[:5]:
                if m['message_type'] == 'warning':
                    st.warning(m['content'], icon="⏰")
                elif m['message_type'] == 'completion':
                    st.success(m['content'], icon="✅")
                else:
                    st.info(m['content'], icon="ℹ️")
        else:
            st.info("No notifications")
    
    if user['role'] == 'manager':
        render_manager_dashboard(supabase, user['id'])
    else:
        render_employee_dashboard(supabase, user['id'], user['full_name'])
