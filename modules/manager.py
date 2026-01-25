import streamlit as st
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from .database import get_employee_stats, send_notification
from .utils import format_datetime_ist, to_ist_timestamp
from .analytics import render_employee_report,render_tasks_table
from .database import get_db
import pandas as pd

supabse = get_db()

def render_manager_dashboard(supabase, manager_id):
    st.header("Manager Dashboard")
    
    st.subheader("✨ Assign New Task")
    employees = supabase.table('users').select("*").eq('role', 'employee').execute()
    emp_options = {e['full_name']: e['id'] for e in employees.data} if employees.data else {}
    emp_names = {e['id'] : e['full_name'] for e in employees.data} if employees.data else {}
    if not emp_options:
        st.warning("No employees found. Create employee accounts first.")
        return
    
    
    st.subheader("Edit Completed Tasks")
    completed_resp = supabase.table('tasks').select("*").eq('status', 'completed').eq('assigned_by', manager_id).execute()
    completed_tasks = completed_resp.data or []

    if not completed_tasks:
        st.info("No completed tasks to edit.")
    else:
        task_options = {f"{t.get('title','Untitled')} (Employee name:{emp_names[t.get('assigned_to')]})": t for t in completed_tasks}
        selected_label = st.selectbox("Select completed task to edit", list(task_options.keys()))
        task = task_options[selected_label]

        with st.form(f"edit_task_{task.get('id')}"):
            col1, col2 = st.columns(2)
            with col1:
                new_title = st.text_input("Title", value=task.get('title', ''))
                new_status = st.selectbox("Status", ['completed', 'in_progress', 'pending'], index=0 if task.get('status') == 'completed' else (1 if task.get('status') == 'in_progress' else 2))
            with col2:
                
                due_date_val = None
                due_time_val = None
                try:
                    if task.get('due_date'):
                        parsed = datetime.fromisoformat(task['due_date'])
                        due_date_val = parsed.date()
                        due_time_val = parsed.time()
                except Exception:
                    pass

                due_date = st.date_input("Due Date", value=due_date_val or datetime.now().date())
                due_time = st.time_input("Due Time (IST)", value=due_time_val or datetime.now().time())

            new_desc = st.text_area("Description", value=task.get('description', ''))
            reopen = st.checkbox("Reopen task (set to in_progress)")
            submit_edit = st.form_submit_button("Save Changes")

            if submit_edit:
                due_iso = to_ist_timestamp(due_date, due_time)
                updated_fields = {
                    'title': new_title,
                    'description': new_desc,
                    'due_date': due_iso,
                    'status': 'in_progress' if reopen else new_status
                }
                supabase.table('tasks').update(updated_fields).eq('id', task.get('id')).execute() 

                try:
                    send_notification(supabase, task.get('assigned_to'), f"✏️ Task '{new_title}' was edited by your manager. Please review.", 'task_edited')
                except Exception as e:
                    print(e)
                    st.write(f"some error: {e}")

                st.success("Task updated successfully.")
                st.rerun()
    


    with st.form("new_task"):
        col1, col2 = st.columns(2)
        with col1:
            target_emp = st.selectbox("Select Employee", list(emp_options.keys()))
            title = st.text_input("Task Title")
        with col2:
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Due Time (IST)")
        
        details = st.text_area("Task Description")
        submit = st.form_submit_button("Assign Task")
        
        if submit and title:
            emp_id = emp_options[target_emp]
            ist = timezone(timedelta(hours=5, minutes=30))
            due_datetime = datetime.combine(due_date, due_time)
            due_datetime_ist = ist.localize(due_datetime) if hasattr(ist, 'localize') else due_datetime.replace(tzinfo=ist)
    
            
            task_data = {
                'title': title, 
                'assigned_to': emp_id, 
                'assigned_by': manager_id,
                'description': details,
                'due_date': due_datetime_ist.isoformat()
            }
            supabase.table('tasks').insert(task_data).execute()
            
            ai_msg = f"✅ New Task: '{title}' - Due {due_date.strftime('%d/%m/%Y')} at {due_time.strftime('%H:%M')} IST"
            send_notification(supabase, emp_id, ai_msg, 'new_task')
            
            st.success(f"✅ Task assigned to {target_emp}!")
            st.rerun()

    st.divider()
    

    st.subheader("👥 Team Progress & Reports")
    team_response = supabase.table('tasks').select("*").eq('assigned_by', manager_id).execute()
    team_tasks = team_response.data or []
    st.subheader("📊 Team Tasks")
    render_tasks_table(team_tasks)
    
    if team_tasks:
        emp_tasks = defaultdict(list)
        emp_ids = set()
        for task in team_tasks:
            emp_tasks[task['assigned_to']].append(task)
            emp_ids.add(task['assigned_to'])
        
        emp_details = {}
        for emp_id in emp_ids:
            emp_res = supabase.table('users').select("*").eq('id', emp_id).execute()
            if emp_res.data:
                emp_details[emp_id] = emp_res.data[0]
        
        for emp_id, tasks in emp_tasks.items():
            if emp_id in emp_details:
                emp_name = emp_details[emp_id]['full_name']
                
                with st.expander(f" {emp_name} - {len(tasks)} tasks"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        for task in tasks:
                            status_color = "🟢" if task['status'] == 'completed' else "🟡"
                            st.write(f"{status_color} **{task['title']}** | {task['progress']}% | {format_datetime_ist(task['due_date'])}")
                    
                    with col2:
                        completed = len([t for t in tasks if t['status'] == 'completed'])
                        rate = (completed / len(tasks)) * 100 if tasks else 0
                        st.metric("Completion", f"{rate:.0f}%")
                    
                    with col3:
                        if st.button("📈 Report", key=f"report_{emp_id}"):
                            st.session_state[f"show_report_{emp_id}"] = True
                    
                    if st.session_state.get(f"show_report_{emp_id}"):
                        st.divider()
                        render_employee_report(supabase, emp_id, emp_name)
    else:
        st.info("No tasks assigned yet.")