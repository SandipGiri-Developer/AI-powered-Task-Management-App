import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
from .utils import format_datetime_ist

def render_metrics(stats):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tasks", stats['total_tasks'])
    with col2:
        st.metric("Completed", stats['completed_tasks'])
    with col3:
        st.metric("Completion %", f"{stats['completion_rate']:.0f}%")
    with col4:
        st.metric("On-Time", stats['on_time'])

def render_pie_chart(completed, pending):
    fig = go.Figure(data=[
        go.Pie(
            labels=['Completed', 'Pending'],
            values=[completed, pending],
            marker=dict(colors=['#2ecc71', '#e74c3c']),
            hole=0.3
        )
    ])
    fig.update_layout(height=400, showlegend=True)
    st.plotly_chart(fig, )

def render_progress_line(tasks):
    tasks_with_dates = [(t['created_at'], t['progress']) for t in tasks if t['created_at']]
    if tasks_with_dates:
        df = pd.DataFrame(tasks_with_dates, columns=['Date', 'Progress'])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        fig = px.line(
            df, 
            x='Date', 
            y='Progress',
            title='Progress Over Time',
            markers=True,
            line_shape='linear'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, )

def render_completion_histogram(tasks):
    if not tasks:
        return
    
    progress_vals = [t['progress'] for t in tasks]
    
    fig = go.Figure(data=[
        go.Histogram(x=progress_vals, nbinsx=10, marker_color='#3498db')
    ])
    fig.update_layout(
        title='Progress Distribution',
        xaxis_title='Progress %',
        yaxis_title='Tasks',
        height=400
    )
    st.plotly_chart(fig, )

def render_status_breakdown(tasks):
    status_counts = {}
    for t in tasks:
        status = t['status'].upper()
        status_counts[status] = status_counts.get(status, 0) + 1
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(status_counts.keys()),
            y=list(status_counts.values()),
            marker_color=['#2ecc71', '#f39c12', '#e74c3c'][:len(status_counts)]
        )
    ])
    fig.update_layout(title='Task Status Breakdown', height=350)
    st.plotly_chart(fig, )

def render_tasks_table(tasks):
    if not tasks:
        st.info("No tasks yet")
        return
    
    task_df = pd.DataFrame([
        {
            'Task': t['title'][:30],
            'Status': t['status'].upper(),
            'Progress': f"{t['progress']}%",
            'Due Date': format_datetime_ist(t['due_date']),
        }
        for t in tasks
    ])
    
    st.dataframe(task_df, hide_index=True)

def render_matplotlib_histogram(progress_values):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(progress_values, bins=10, color='#3498db', edgecolor='black', alpha=0.7)
    ax.set_xlabel('Progress %')
    ax.set_ylabel('Count')
    ax.set_title('Task Progress Distribution')
    ax.grid(axis='y', alpha=0.3)
    st.pyplot(fig)

def render_performance_gauge(completion_rate):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=completion_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Completion Rate"},
        delta={'reference': 80},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "#f39c12"},
                {'range': [50, 80], 'color': "#2ecc71"},
                {'range': [80, 100], 'color': "#27ae60"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=400)
    st.plotly_chart(fig, )

def render_time_series(tasks):
    tasks_sorted = sorted([t for t in tasks if t['created_at']], key=lambda x: x['created_at'])
    
    if not tasks_sorted:
        return
    
    dates = [pd.to_datetime(t['created_at']) for t in tasks_sorted]
    progress = [t['progress'] for t in tasks_sorted]
    
    fig = px.line(
        x=dates,
        y=progress,
        title='Task Progress Timeline',
        markers=True,
        labels={'x': 'Date', 'y': 'Progres s %'}
    )
    fig.update_layout(height=400, hovermode='x unified')
    st.plotly_chart(fig, )

def render_employee_report(supabase, employee_id, employee_name):
    from .database import get_employee_stats
    from .ai_service import gen_performance_analysis
    
    stats = get_employee_stats(supabase, employee_id)
    
    st.markdown(f"## 📊 {employee_name} Performance Report")
    render_metrics(stats)
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if stats['completed_tasks'] > 0 or stats['pending_tasks'] > 0:
            render_pie_chart(stats['completed_tasks'], stats['pending_tasks'])
    
    with col2:
        progress_vals = [t['progress'] for t in stats['tasks']]
        if progress_vals:
            render_matplotlib_histogram(progress_vals)
    
    st.divider()
    st.markdown("### 🤖 AI Analysis")
    ai_analysis = gen_performance_analysis(employee_name, stats)
    st.info(ai_analysis)
