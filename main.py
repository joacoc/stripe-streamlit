import streamlit as st
import psycopg
import altair as alt
import threading
import queue
import pandas as pd
import os
from collections import defaultdict
import altair as alt
from vega_datasets import data

# DATABASE_URL = "postgres://<USER>:<PASS>@<HOST>:6875/materialize?sslmode=require"
DATABASE_URL = os.environ['DATABASE_URL']

# Style the page
st.markdown(
    """
<link href='https://fonts.googleapis.com/css?family=VT323' rel='stylesheet'>
<style>
body {
    background: '#000000';
}
div {
    font-family: 'VT323';
}

div[data-testid="metric-container"] > div > div {
    font-family: 'VT323';
}
div[data-testid="metric-container"] > label[data-testid="stMetricLabel"] > div p {
   font-size: 200% !important;
   font-family: 'VT323';
}
div[data-testid="metric-container"] > div[data-testid="stMetricDelta"] > div {
   font-size: 150% !important;
}
</style>
""",
    unsafe_allow_html=True,
)
st.title('Stripe Dashboard')

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
        );"""):
            # print(f"Row from database: {row}")  # Log the fetched row for debugging
            updates_queue.put(row)

# Create a background thread to fetch data
thread = threading.Thread(target=fetch_data)
thread.start()

# Initialize the session state
if 'data' not in st.session_state:
    st.session_state['volume'] = None
    st.session_state['total_transactions'] = None
    st.session_state['transactions_per_minute'] = None

# Placeholder
ph = st.empty()

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
            ph.empty()
            col1, col2, col3 = ph.columns(3)
            col1.metric(label="Volume", value=f"${st.session_state['volume']:n}", delta="%10")
            col2.metric(label="Total transactions", value=st.session_state['total_transactions'], delta="%10 in the last minute")
            col3.metric(label="Transactions per minute", value=st.session_state['transactions_per_minute'], help="Total transactions in the last minute.", delta="%5")

