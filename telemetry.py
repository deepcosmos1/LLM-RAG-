from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
from dotenv import load_dotenv
import uuid

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from groq import Groq
import sqlparse

from supabase import create_client, Client
import supabase

load_dotenv()
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

llm = ChatGroq(
    groq_api_key=os.environ.get("GROQ_API_KEY"),
    model_name="llama3-70b-8192",
    temperature=0.1,
)


housekeeping_data_db_schema = '''
CREATE TABLE telemetry_data (
    timestamp TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT,  -- Assuming 'value' can store text or numerical data
    calibrated_value TEXT,  
    unit TEXT,
    c_func TEXT
);

'''

def query_conv(user_query):
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY")
    )

    query_prompt = f"""
### Task
Generate a SQL query to answer [QUESTION]{user_query}[/QUESTION] about satellite housekeeping data.

## Database Schema:
{housekeeping_data_db_schema}

## Information about Data attributes:
1. timestamp: The date and time of the data entry.
2. name: The type of measurement or event recorded (e.g., uptime, eps_battery, software_ident, safe_mode, AMRAD_message).
3. value: The raw value of the measurement.
4. calibrated_value: A potentially processed or calibrated value (though this column seems mostly empty).
5. unit: The units associated with the values (e.g., seconds for time measurements).
6. c_func: Possibly a column for function or additional metadata.

## Satellite Housekeeping Data Context:
This data represents various metrics and events from an Amateur Radio Satellite, including power levels, battery status, temperature, RSSI, and system messages.

## Instructions
- Provide a SQL query that answers the user's question about satellite housekeeping data.
- If you cannot answer the question with the available database schema, return 'I don't know'.
- Focus on retrieving relevant data for satellite metrics, events, and status information.

### Answer
Given the database schema, here is the SQL query that answers [QUESTION]{user_query}[/QUESTION]
Response only in [SQL] format and do not include any other information.
"""

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": query_prompt,
            },
            {
                "role": "user",
                "content": user_query,
            },
        ],
        model="llama3-70b-8192",
    )

    query = chat_completion.choices[0].message.content
    sql_query = sqlparse.format(query, reindent=True)
    return sql_query


SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Use your Database API endpoint here to query the database and return result
def execute_sql_query(sql_query):
    if sql_query == "I don't know":
        return "I don't know"

    # #API here  
    response = supabase.table("telemetry_data").select("*", count="exact").execute()
    return response


def generate_nl_response(user_query, sql_query, query_results):
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    prompt = f"""
### Task
Generate a natural language response to the user's query about satellite housekeeping data based on the SQL query results.

### User Query
{user_query}

### SQL Query
{sql_query}

### Query Results
{query_results}

## Database Schema:
{housekeeping_data_db_schema}

## Information about Data attributes:
1. timestamp: The date and time of the data entry.
2. name: The type of measurement or event recorded (e.g., uptime, eps_battery, software_ident, safe_mode, AMRAD_message).
3. value: The raw value of the measurement.
4. calibrated_value: A potentially processed or calibrated value (though this column seems mostly empty).
5. unit: The units associated with the values (e.g., seconds for time measurements).
6. c_func: Possibly a column for function or additional metadata.


## Instructions
- Provide a short, clear and concise, to the point answer to the user's query about satellite housekeeping data.
- Interpret the query results in the context of satellite operations and metrics.
- If specific data is requested, present it clearly and explain its significance.
- Avoid mentioning SQL or database operations in your response.
- If you cannot answer the question with the available data, say "I don't have enough information to answer that question."

"""

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": prompt,
            }
        ],
        model="llama3-70b-8192",
    )

    return chat_completion.choices[0].message.content

system_prompt = """You are an expert in satellite housekeeping data analysis. Your role is to assist users by answering questions about Amateur Radio Satellite data, including power levels, battery status, temperature, RSSI, system messages, and other relevant metrics. Use your knowledge to provide insightful answers and explanations about satellite operations and status. If you cannot answer a question, say "I don't have enough information to answer that question."
"""

user_conversations = {}

@socketio.on('connect')
def handle_connect():
    user_id = str(uuid.uuid4())
    join_room(user_id)
    emit('set_user_id', {'user_id': user_id})
    print(f'Client connected with ID: {user_id}')

@socketio.on('join')
def on_join(data):
    user_id = data['user_id']
    join_room(user_id)
    print(f'User {user_id} joined their room')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('user_message')
def handle_message(message):
    user_id = message['user_id']
    user_query = message['data']
    print(f'User {user_id}: {user_query}')

    if user_id not in user_conversations:
        memory = ConversationBufferMemory(return_messages=True)
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])
        user_conversations[user_id] = ConversationChain(
            llm=llm,
            memory=memory,
            prompt=prompt,
            verbose=False
        )

    conversation = user_conversations[user_id]
    
    sql_query = query_conv(user_query)
    print('Generated SQL query:', sql_query)
    
    query_results = execute_sql_query(sql_query)
    print('Query results:', query_results)
    
    nl_response = generate_nl_response(user_query, sql_query, query_results)
    print('Natural language response:', nl_response)
    
    conversation.predict(input=f"User: {user_query}\nAI: {nl_response}")
    
    emit('bot_response', {'data': nl_response}, room=user_id)

if __name__ == '__main__':
    socketio.run(app, debug=False)