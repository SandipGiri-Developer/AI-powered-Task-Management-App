import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta, timezone
from .utils import get_ist_now
import logging
import os
from dotenv import load_dotenv
load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_supabase = None
#getting single supabse client
def get_db():
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
        key = os.getenv("SUPABASE_KEY") or st.secrets["SUPABASE_KEY"]
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

def create_task( title, desc, emp_id, manager_id, due_datetime_iso,supabase = get_db()):
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
# ----- EMAIL & WHATSAPP UTILITIES -----

def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send email via SendGrid or SMTP (if configured).
    Returns True if sent, False otherwise.
    """
    sendgrid_key = os.getenv("SENDGRID_API_KEY", "")
    smtp_server = os.getenv("SMTP_SERVER", "")
    
    if sendgrid_key:
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email='noreply@jayashreepolymers.com',
                to_emails=to_email,
                subject=subject,
                html_content=html_body
            )
            sg = SendGridAPIClient(sendgrid_key)
            response = sg.send(message)
            logger.info(f"Email sent to {to_email}: {response.status_code}")
            return response.status_code in [200, 202]
        except Exception as e:
            logger.error(f"Error sending email via SendGrid: {e}")
            return False
    
    elif smtp_server:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_user
            msg['To'] = to_email
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, to_email, msg.as_string())
            
            logger.info(f"Email sent to {to_email} via SMTP")
            return True
        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}")
            return False
    else:
        logger.warning("No email service configured")
        return False

def send_whatsapp(to_number: str, message: str) -> bool:
    """
    Send WhatsApp message via Twilio.
    to_number: 'whatsapp:+919876543210'
    Returns True if sent, False otherwise.
    """
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_num = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        
        if not account_sid or not auth_token:
            logger.warning("Twilio credentials not configured")
            return False
        
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=from_num,
            body=message,
            to=to_number
        )
        logger.info(f"WhatsApp sent to {to_number}: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Error sending WhatsApp: {e}")
        return False