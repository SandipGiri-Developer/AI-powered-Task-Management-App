import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
from .utils import get_ist_now

_supabase = None

def get_db():
    global _supabase
    if _supabase is None:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        _supabase = create_client(url, key)
    return _supabase

def get_employee_stats(supabase, employee_id, days=15):
    ist = timezone(timedelta(hours=5, minutes=30))
    
    resp = supabase.table('tasks').select("*").eq('assigned_to', employee_id).execute()
    tasks = resp.data or []
    
    stats = {
        'total_tasks': len(tasks),
        'completed_tasks': len([t for t in tasks if t['status'] == 'completed']),
        'pending_tasks': len([t for t in tasks if t['status'] == 'pending']),
        'completion_rate': 0,
        'on_time': 0,
        'delayed': 0,
        'avg_progress': 0,
        'tasks': tasks
    }
    
    if stats['total_tasks'] > 0:
        stats['completion_rate'] = (stats['completed_tasks'] / stats['total_tasks']) * 100
        stats['avg_progress'] = sum(t['progress'] for t in tasks) / stats['total_tasks']
    
    now = get_ist_now()
    for task in tasks:
        if task['status'] == 'completed' and task['due_date']:
            due = datetime.fromisoformat(task['due_date']).astimezone(ist)
            if due >= now:
                stats['on_time'] += 1
            else:
                stats['delayed'] += 1
    
    return stats

def get_team_tasks(supabase, manager_id):
    resp = supabase.table('tasks').select("*").eq('assigned_by', manager_id).execute()
    return resp.data or []

def get_employee_details(supabase, emp_id):
    resp = supabase.table('users').select("*").eq('id', emp_id).execute()
    return resp.data[0] if resp.data else None

def create_task(supabase, title, desc, emp_id, manager_id, due_datetime_iso):
    task_data = {
        'title': title,
        'assigned_to': emp_id,
        'assigned_by': manager_id,
        'description': desc,
        'due_date': due_datetime_iso
    }
    supabase.table('tasks').insert(task_data).execute()

def send_notification(supabase, recipient_id, content, msg_type):
    supabase.table('messages').insert({
        'recipient_id': recipient_id,
        'content': content,
        'message_type': msg_type
    }).execute()

def get_notifications(supabase, user_id):
    resp = supabase.table('messages').select("*").eq('recipient_id', user_id).order('created_at', desc=True).execute()
    return resp.data or []

def check_all_deadlines(supabase):
    ist = timezone(timedelta(hours=5, minutes=30))
    now = get_ist_now()
    warning_time = now + timedelta(hours=24)

    resp = supabase.table('tasks').select("*").eq('status', 'pending').execute()
    tasks = resp.data or []

    for task in tasks:
        if task.get('warning_sent'):
            continue
            
        due_date = datetime.fromisoformat(task['due_date']).astimezone(ist) if task['due_date'] else None
        
        if due_date and now < due_date < warning_time and task['progress'] < 100:
            msg = f"⏰ URGENT: Task '{task['title']}' is due in less than 24 hours!"
            
            send_notification(supabase, task['assigned_to'], msg, 'warning')
            send_notification(supabase, task['assigned_by'], msg, 'warning')
            
            supabase.table('tasks').update({'warning_sent': True}).eq('id', task['id']).execute()
