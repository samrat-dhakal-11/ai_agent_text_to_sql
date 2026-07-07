Campus Query — Intelligent SQL Chatbot
Campus Query is a secure, persistent AI-powered interface that allows users to interact with complex academic databases using natural language. Built with LangGraph and Groq, it provides a robust SQL interaction layer featuring user authentication, conversation persistence, and strict security guardrails.
Key Features
•	Secure Authentication: User accounts managed via app_data.db using PBKDF2-SHA256 password hashing.
•	Persistent Conversations: Full history logging; sessions are saved and reloaded automatically via SQLite.
•	Safety First: Multi-layered guardrails block prompt injection, sanitize inputs, and enforce read-only SQL (blocking any INSERT, UPDATE, DELETE, or DROP commands).
•	Dynamic Data: Operates on an expanded academic schema including students, departments, course enrollments, and attendance tracking.
Technical Architecture
Component	Responsibility
Streamlit	Interactive web interface and session state management.
LangGraph	Orchestration of the SQL Agent and tool execution flow.
Groq API	High-performance LLM inference for natural language queries.
SQLite	Local persistence for both user data and academic datasets.
Getting Started
Prerequisites
•	Python 3.12+
•	Groq API Key
Setup
	1.	Install Dependencies:
pip install -r requirements.txt

	2.	Configure Environment:
cp .env.example .env
# Add your GROQ_API_KEY to the .env file

Execution
Launch the application locally:
streamlit run app.py

Access the interface via the URL provided in your terminal (typically http://localhost:8501).
Database Schema
The application utilizes a relational structure to support complex querying capabilities:
•	Students & Departments: Demographic and academic standing.
•	Courses & Instructors: Metadata for curriculum management.
•	Enrollments & Attendance: Time-series and relational data for reporting.
To reset the academic dataset, simply delete students.db and restart the application.
Security Notice
This application is designed with a "secure-by-default" philosophy. The SQL Guardrail logic acts as a middleware, ensuring that the AI agent's generated queries are validated against an allow-list of read-only keywords before any database execution occurs.