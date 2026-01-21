import streamlit as st

st.set_page_config(page_title="Task Management System", layout="wide")

from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager
from modules.database import check_all_deadlines, get_db
from modules.manager import render_manager_dashboard
from modules.employee import render_employee_dashboard

cookies = EncryptedCookieManager(prefix="task_app", password="secret_key_123")
if not cookies.ready():
    st.stop()

supabase = get_db()

check_all_deadlines(supabase)


if 'checked' not in st.session_state:
    check_all_deadlines(supabase)
    st.session_state['checked'] = True

if 'user' not in st.session_state and cookies.get('user'):
    uid = cookies['user']
    res = supabase.table('users').select("*").eq('id', uid).execute()
    if res.data:
        st.session_state['user'] = res.data[0]

if 'user' not in st.session_state:
    st.title(" Login / Signup")
    mode = st.radio("", ["Login", "Sign Up"], horizontal=True)
    
    if mode == "Sign Up":
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["manager", "employee"])
        if st.button("Register"):
            try:
                supabase.table('users').insert({
                    'email': email,
                    'full_name': name,
                    'role': role
                }).execute()
                st.success("✅ Registered! Switch to Login.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        email = st.text_input("Email")
        if st.button("Login"):
            resp = supabase.table('users').select("*").eq('email', email).execute()
            if resp.data:
                st.session_state['user'] = resp.data[0]
                cookies['user'] = str(resp.data[0]['id'])
                cookies.save()
                st.rerun()
            else:
                st.error("User not found")

else:
    user = st.session_state['user']
    
    with st.sidebar:
        st.write(f"**{user['full_name']}** ({user['role']})")

        if st.button("Logout"):
            cookies['user'] = ""
            cookies.save()
            if 'user' in st.session_state:
                del st.session_state['user']
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
