# Groq-SQL-Agent

### Features:
1. Websockets-powered chatbots for real-time Communication.
2. Chatbots are equipped with Session memory (Until you refresh, the chatbot remembers the previous conversation)
3. GROQ-LLM used for Ultra-Fast responses.
4. Multiple users can use it simultaneously. (The concept of UUID and rooms is implemented)
5. LangChain is used for the efficient orchestration of functions.

### How to run locally ?

1. Clone the repo
  ```bash
  https://github.com/Spyrosigma/Groq-SQL-Agent.git
  ```

2. Install necessary modules
  ```bash
  pip install -r requirements.txt
  ```

3. Create a .env file and fill in the creds:
  - GROQ_API_KEY
  - Your Database URL and API key (You've to set it up)

4. There are 2 Agents, run them with these commands:

   - Satellite Image Agent
      ```bash
      python satellite.py
      ```
   - Housekeeping Satellite Agent
      ```bash
      python telementry.py  
      ```

5. Run the index.html file for Chatbot Interaction.

  
