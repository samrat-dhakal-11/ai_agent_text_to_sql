Campus Query — Intelligent SQL Chatbot

Campus Query is a secure, persistent AI-powered interface that enables natural language interaction with complex academic databases.

🚀 Key Features
•	Secure Authentication: User accounts managed via app_data.db using PBKDF2-SHA256 password hashing.

•	Persistent Conversations: History logging with automated session reloading via SQLite.

•	Safety First: Multi-layered guardrails block prompt injection and enforce
	read-only SQL (blocking INSERT, UPDATE, DELETE, and DROP).

•	Dynamic Data: Expanded academic schema including students, departments, course enrollments, and attendance.


🛠 Technical Architecture
Component	Responsibility
Streamlit	Interactive UI and session state management.
LangGraph	Orchestration of SQL Agent and tool execution flow.
Groq API	High-performance LLM inference.
SQLite	Local persistence for user data and academic datasets.

⚙️ Getting Started
Prerequisites
•	Python 3.12+
•	Groq API Key
Setup & Execution
	1.	Install Dependencies:
pip install -r requirements.txt

	2.	Configure Environment:
cp .env.example .env
# Add your GROQ_API_KEY to the .env file

	3.	Run Application:
streamlit run app.py

Access via http://localhost:8501
🗄 Database Schema
The application utilizes a relational structure for advanced querying:
•	Students & Departments: Demographic and academic standing.
•	Courses & Instructors: Curriculum management metadata.
•	Enrollments & Attendance: Time-series and relational reporting data.
Note: To reset the academic dataset, delete students.db and restart the application.
🛡 Security Notice
The SQL Guardrail logic functions as middleware, validating all AI-generated queries against an allow-list of read-only keywords before execution to ensure system integrity.