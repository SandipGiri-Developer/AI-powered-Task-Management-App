import streamlit as st
import google.generativeai as genai

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def gen_ai_response(prompt: str) -> str:
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating response: {str(e)}"

def gen_performance_analysis(emp_name: str, stats: dict) -> str:
    prompt = f"""
Analyze this employee's performance and provide insights:

Employee: {emp_name}
Total Tasks: {stats['total_tasks']}
Completed Tasks: {stats['completed_tasks']}
Completion Rate: {stats['completion_rate']:.1f}%
On-Time Completions: {stats['on_time']}
Delayed Completions: {stats['delayed']}

Provide a brief, professional performance analysis with:
1. Productivity assessment
2. Timeliness evaluation (pressure handling score)
3. Consistency remarks
4. Specific recommendation for improvement

Keep it concise and actionable.
    """
    return gen_ai_response(prompt)

def gen_task_summary(task_title: str, task_desc: str, progress: int) -> str:
    prompt = f"""
Generate a brief update message for this task:
Title: {task_title}
Description: {task_desc}
Progress: {progress}%

Make it motivational and concise.
    """
    return gen_ai_response(prompt)

def gen_deadline_alert(task_title: str, hours_left: int) -> str:
    prompt = f"""
Generate an urgent deadline reminder for:
Task: {task_title}
Hours Left: {hours_left}

Make it motivating but urgent. Keep it 1-2 sentences.
    """
    return gen_ai_response(prompt)
