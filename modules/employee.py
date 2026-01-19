import streamlit as st
from .database import get_notifications, send_notification
from .utils import format_datetime_ist

def render_employee_dashboard(supabase, user_id, user_name):
    st.header("📝 My Tasks")
    
    render_alerts_section(supabase, user_id)
    st.divider()
    render_tasks_section(supabase, user_id, user_name)

def render_alerts_section(supabase, user_id):
    st.subheader("🔔 Your Alerts")
    msgs = get_notifications(supabase, user_id)
    
    if msgs:
        for m in msgs:
            if m['message_type'] == 'warning':
                st.warning(m['content'])
            elif m['message_type'] == 'completion':
                st.success(m['content'])
            else:
                st.info(m['content'])
    else:
        st.info("No alerts")

def render_tasks_section(supabase, user_id, user_name):
    resp = supabase.table('tasks').select("*").eq('assigned_to', user_id).execute()
    my_tasks = resp.data or []
    
    if not my_tasks:
        st.info("No tasks assigned yet.")
        return
    
    completed = [t for t in my_tasks if t['status'] == 'completed']
    pending = [t for t in my_tasks if t['status'] == 'pending']
    
    if pending:
        st.subheader("⏳ Pending Tasks")
        for task in pending:
            render_pending_task(supabase, task, user_name)
    
    if completed:
        st.subheader("✅ Completed Tasks")
        for task in completed:
            with st.container(border=True):
                st.write(f"### {task['title']}")
                st.write(f"📅 {format_datetime_ist(task['due_date'])}")
                st.write("Status: ✅ COMPLETED")

def render_pending_task(supabase, task, user_name):
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.write(f"### {task['title']}")
            if task['description']:
                st.write(f"**Desc:** {task['description']}")
            st.write(f"📅 **Due:** {format_datetime_ist(task['due_date'])}")
        
        with col2:
            new_prog = st.slider("Progress", 0, 100, task['progress'], key=f"p_{task['id']}", label_visibility="collapsed")
            
            if st.button("💾 Save", key=f"s_{task['id']}", use_container_width=True):
                status = 'completed' if new_prog == 100 else 'pending'
                supabase.table('tasks').update({
                    'progress': new_prog,
                    'status': status
                }).eq('id', task['id']).execute()
                
                if new_prog == 100:
                    msg = f"✅ '{task['title']}' completed by {user_name}!"
                    send_notification(supabase, task['assigned_by'], msg, 'completion')
                    st.success("✅ Completed! Manager notified.")
                else:
                    st.success(f"💾 {new_prog}%")
                
                st.rerun()
