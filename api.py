from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List
import re
from datetime import datetime
import requests
import streamlit as st
import threading
import uvicorn

# FastAPI setup
app = FastAPI()

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["taskab"]
collection = db["schedules"]

class Task(BaseModel):
    task: str
    time: str

class Query(BaseModel):
    ques: str

# FastAPI routes
@app.post("/schedule_task/")
async def schedule_task(query: Query):
    try:
        ques = query.ques.lower()
        if "task" in ques or "schedule" in ques or "scheduler" in ques:
            result = await task_scheduler(ques)
            return result
        # elif "hi" in ques and len(ques)==2:
        #     return "Hi, I am your personal chatbot here to assist you."
        elif "hello" in ques and len(ques)==2:
            return "Hello, I am your personal chatbot here to assist you."
        elif "hey" in ques:
            return "Hey, I am your personal chatbot here to assist you."
        elif "your purpose" in ques:
            return "I am a personal chatbot. I can assist you with scheduling tasks and informing you with general knowledge."
        else:
            result = await wiki_answer(ques)
            return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def wiki_answer(command: str):
    if 'who is' in command:
        wiki = command.replace('who is', '').strip()
    elif 'what is' in command:
        wiki = command.replace('what is', '').strip()
    elif 'where is' in command:
        wiki = command.replace('where is', '').strip()
    elif 'when is' in command:
        wiki = command.replace('when is', '').strip()
    elif 'why is' in command:
        wiki = command.replace('why is', '').strip()
    elif 'tell me about' in command:
        wiki = command.replace('tell me about', '').strip()
    elif 'what are' in command:
        wiki = command.replace('what are', '').strip()
    elif 'who are' in command:
        wiki = command.replace('who are', '').strip()
    elif 'where are' in command:
        wiki = command.replace('where are', '').strip()
    elif 'when are' in command:
        wiki = command.replace('when are', '').strip()
    elif 'why are' in command:
        wiki = command.replace('why are', '').strip()
    elif 'tell me about' in command:
        wiki = command.replace('tell me about', '').strip()
    elif 'define' in command.lower():
        wiki = command.replace('define', '', re.IGNORECASE).strip()
    else:
        return "Sorry, I didn't understand the question."
    info = get_wikipedia_summary(wiki)
    return info


def get_wikipedia_summary(query: str, sentences: int = 2) -> str:
    try:
        headers = {
            'User-Agent': 'main/1.0 (kalkeeshjamipics@gmail.com)'
        }
        response = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}", headers=headers)
        data = response.json()
        if 'extract' in data:
            summary = data['extract']
            summary_sentences = '. '.join(summary.split('. ')[:sentences])
            return summary_sentences
        else:
            return "Sorry, I couldn't find any information on that topic."
    except Exception as e:
        return f"An error occurred: {e}"

async def task_scheduler(ques: str):
    task_match = re.search(r'-(.*?)\sat', ques)
    task = task_match.group(1).strip() if task_match else "No specific task mentioned"
    time_match = re.search(r'\b\d{1,2}:\d{2}\s*[APMapm]{2}\b', ques.upper())
    
    if not time_match:
        raise ValueError("No valid time format found in the query.")
    
    time_str = time_match.group(0).strip().upper()
    time_obj = datetime.strptime(time_str, '%I:%M %p')
    formatted_time = time_obj.strftime('%I:%M %p')
    
    # Store the task and time in MongoDB
    task_data = {"task": task, "time": formatted_time}
    collection.insert_one(task_data)
    
    return {"task scheduled"}
    # Function definition remains the same as before

@app.get("/tasks/")
async def get_tasks():
    tasks = list(collection.find())
    for task in tasks:
        task['_id'] = str(task['_id'])
    return tasks

@app.delete("/delete_task/")
async def delete_task(task_name: str):
    result = collection.delete_one({"task": task_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Streamlit setup
st.set_page_config(page_title="FactBuddy Chat Bot", page_icon=":robot_face:", layout="centered")

def display_instructions():
    with st.expander("ℹ️ Instructions"):
        st.markdown("""
        ### How to Use FactBuddy Chat Bot:
        -**The chatbot can only answer the WH questions**
        - **Search for Facts**: Use the search bar to find quick information.
        - **Schedule a Task**: To schedule a task, your prompt should include:
          - The words **"schedule"** or **"task"**.
          - The task name should start with a **"-"** and end with **"at"**.
          - The time given should definitely contain **am** or **pm**.
        - **Case Insensitive**: The prompt is case insensitive.
        - **The tasks can be erased one at a time**.
        -**The tasks cann be completed one at a time.**
        """)

def section_title(title, color):
    st.markdown(f"<h2 style='color: {color};'>{title}</h2>", unsafe_allow_html=True)

def main():
    st.title("FactBuddy Chat Bot :robot_face:")
    st.markdown("<h4 style='text-align: center; color: grey;'>Your smart assistant for task scheduling and quick information.</h4>", unsafe_allow_html=True)

    show_instructions = st.button("ℹ️ Instructions")
    if show_instructions:
        display_instructions()

    with st.container():
        section_title("talk to me buddy", "#FF6347")
        with st.form(key='schedule_task_form'):
            col1, col2 = st.columns([4, 1])
            with col1:
                ques = st.text_input("Enter your query buddy")
            with col2:
                submit_button = st.form_submit_button(label="search")
            if submit_button:
                response = requests.post("http://localhost:8000/schedule_task/", json={"ques": ques})
                if response.status_code == 200:
                    st.success(response.json())
                else:
                    st.error(response.json()["detail"])

    with st.container():
        section_title("Planned Activities", "#32CD32")
        get_tasks_response = requests.get("http://localhost:8000/tasks/")
        if get_tasks_response.status_code == 200:
            tasks = get_tasks_response.json()
            if tasks:
                selected_tasks = []
                for index, task in enumerate(tasks):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.checkbox(f"Task: {task['task']} at {task['time']}", key=f"task_{index}"):
                            selected_tasks.append(task['task'])

                if st.button("Completed Task"):
                    for task_name in selected_tasks:
                        delete_response = requests.delete("http://localhost:8000/delete_task/", params={"task_name": task_name})
                        if delete_response.status_code == 200:
                            st.success(f"Deleted task: {task_name}")
                        else:
                            st.error(f"Failed to delete task: {task_name}")
            else:
                st.write("No tasks available for management.")
        else:
            st.error("Failed to retrieve tasks.")

    st.markdown("---")

    if __name__ == "__main__":
        st.title("Chatbot Task Operations")

if __name__ == '__main__':
    threading.Thread(target=uvicorn.run, args=(app,)).start()
    main()
