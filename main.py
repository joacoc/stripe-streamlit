import streamlit as st
import psycopg
import threading
import queue
import os
import streamlit.components.v1 as components

# DATABASE_URL = "postgres://<USER>:<PASS>@<HOST>:6875/materialize?sslmode=require"
DATABASE_URL = os.environ['DATABASE_URL']

style = """
<link href='https://fonts.googleapis.com/css?family=VT323' rel='stylesheet'>
<style>
body {
    background: '#000000';
}
div {
    font-family: 'VT323' !important;;
}

div[data-testid="metric-container"] > div > div {
    font-family: 'VT323' !important;
    font-size: 200% !important;
}
div[data-testid="metric-container"] > label[data-testid="stMetricLabel"] > div p {
   font-size: 200% !important;
   font-family: 'VT323' !important;
}
div[data-testid="metric-container"] > div[data-testid="stMetricDelta"] > div {
   font-size: 150% !important;
}
</style>
"""

# Style the page
st.set_page_config(
    page_title="real-time", page_icon="🟢", initial_sidebar_state="collapsed"
)
st.markdown(style, unsafe_allow_html=True,)
st.title('Real-time Dashboard')

# Fetch using SUBSCRIBE and add to a queue.
# Later we are going to process the queue and render the components
# only when a new update arrives.
updates_queue = queue.Queue()
def fetch_data():
    conn = psycopg.connect(DATABASE_URL)
    with conn.cursor() as cur:
        for row in cur.stream("""SUBSCRIBE (
            SELECT volume::text as "value", 'volume' as "metric" FROM volume
            UNION ALL
            SELECT total::text as "value", 'total_transactions' as "metric"  FROM total_transactions
            UNION ALL
            SELECT last_minute_total::text as "value", 'last_minute_total' as "metric"  FROM last_minute_transactions
            UNION ALL
            SELECT subscriptions::text as "value", 'total_subscriptions' as "metric" FROM total_subscriptions
            UNION ALL
            SELECT fraudulent::text as "value", 'total_fraudulent' as "metric" FROM total_fraudulent
        );"""):
            updates_queue.put(row)

# Create a background thread to fetch data
thread = threading.Thread(target=fetch_data)
thread.start()

# Initialize the session state
if 'data' not in st.session_state:
    st.session_state['volume'] = None
    st.session_state['total_transactions'] = None
    st.session_state['last_minute_total'] = None
    st.session_state['total_subscriptions'] = None
    st.session_state['total_fraudulent'] = None

# Placeholder
ph = st.empty()
ph.markdown(style, unsafe_allow_html=True,)

while True:
    if not updates_queue.empty():
        print("Data found in queue!")  # Check if we're ever entering this block
        update = updates_queue.get()
        print(f"Update received: {update}")  # Log the received update for debugging

        if "Error" in update:
            st.error(update)
        else:
            # Append data to session state
            st.session_state[update[3]] = int(update[2])
            print("Update metrics!")  # Check if we're ever entering this block
            ph = ph.empty()
            container = ph.container()
            col1, col2, col3 = container.columns(3)
            col2.metric(label="Volume", value=f"${st.session_state['volume']}", delta="‎")

            col1, col2 = container.columns(2)
            col1.metric(label="Total transactions", value=f"{st.session_state['total_transactions']}")
            col2.metric(label="Transactions per minute", value=st.session_state['last_minute_total'], help="Total transactions in the last minute.")

            col1, col2 = container.columns(2)
            col1.metric(label="Total subscriptions", value=st.session_state['total_subscriptions'])
            col2.metric(label="Fraudulent cases", value=st.session_state['total_fraudulent'])