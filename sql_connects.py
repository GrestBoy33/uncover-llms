import sqlite3





DB_FILENAME = "chat_history.db"

def init_db():
    """Initializes the SQLite database with sessions and chat_history tables."""
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    session_name TEXT,
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    session_name TEXT,
                    sender TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                 )''')
    c.execute("""
        CREATE TABLE IF NOT EXISTS endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            port INTEGER,
            protocol TEXT,
            api_key TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def fetch_all():
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("SELECT session_id,session_name FROM sessions order by created DESC ")
    rows = c.fetchall()
    conn.close()
    return rows

def create_session(session_id):
    """Creates a new session record if it doesn't already exist."""
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sessions (session_id,session_name) VALUES (?,?)", (session_id,session_id))
    conn.commit()
    conn.close()


def delete_session(session_id):
    """Deletes a session and all associated chat history."""
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()

    try:
        # Delete chat history related to the session
        c.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))

        # Delete the session itself
        c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        conn.commit()
    except Exception as e:
        print(f"Error deleting session: {e}")
        conn.rollback()
    finally:
        conn.close()
def update_messages(session_id,user_input,user_type):
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
        # Insert user's message
    c.execute("INSERT INTO chat_history (session_id, sender, message) VALUES (?, ?, ?)",
                  (session_id, user_type, user_input))
        # Insert AI's response
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    """Returns a list of chat messages (as dcc.Markdown components) for the given session."""
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("SELECT sender, message FROM chat_history WHERE session_id=? ORDER BY timestamp", (session_id,))
    rows = c.fetchall()
    conn.close()

    return rows

def get_conversation_context(session_id):
    """Retrieve the conversation history for a given session from SQLite."""
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    # Assuming your sessions table stores a unique session name and chat_history stores the conversation
    c.execute("""
        SELECT sender,message 
        FROM chat_history 
        WHERE session_id = ?
        ORDER BY timestamp 
    """, (session_id,))
    rows = c.fetchall()
    conn.close()
    context = ""
    for user_input, ai_response in rows:
        # Only include entries where both question and response exist
            context += f"User: {user_input}\nAI: {ai_response}\n"
    return context


def update_session_name(new_name, session_id):
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("UPDATE sessions SET session_name=? WHERE session_id=?", (new_name, session_id))
    conn.commit()
    conn.close()

def update_private_endpoint(url, port, protocol, api_key):
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO endpoints (url, port, protocol, api_key)
        VALUES (?, ?, ?, ?)
    """, (url, port, protocol, api_key))
    conn.commit()
    conn.close()

def fetch_private_endpoint():
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    # Assuming your sessions table stores a unique session name and chat_history stores the conversation
    c.execute("""
        SELECT * from endpoints order by timestamp desc""")
    rows = c.fetchall()
    conn.close()
    return rows



