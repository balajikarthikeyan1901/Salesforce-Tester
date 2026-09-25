import streamlit as st
import google.generativeai as genai
from simple_salesforce import Salesforce
import sys
from io import StringIO

# --- PAGE SETUP ---
st.set_page_config(page_title="Salesforce Test Automation", layout="wide")
st.title("Salesforce AI Test Automation Portal")

# --- 1. SECRETS & CREDENTIALS ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = st.sidebar.text_input("Gemini API Key", type="password")

st.sidebar.header("Salesforce Staging Credentials")
username = st.sidebar.text_input("Salesforce Username")
password = st.sidebar.text_input("Salesforce Password", type="password")
security_token = st.sidebar.text_input("Security Token", type="password")

# Initialize memory so the app doesn't forget the code when you click a button
if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""
if "execution_logs" not in st.session_state:
    st.session_state.execution_logs = ""

# --- 2. TEST CASE GENERATION (WITH TEMPLATES) ---
st.header("Step 1: Generate Test Case")

template_options = {
    "Custom Test Case (Type your own below)": "",
    "Create & Validate Account": "Create an Account named 'Test Corp', check that Industry is set to 'Technology', and verify the record exists.",
    "Create Lead & Convert": "Create a new Lead with status 'Open', convert it, and assert that an Opportunity was successfully generated.",
    "Test Validation Rule": "Attempt to create a Contact without a Last Name and verify that Salesforce returns a validation error."
}

selected_template = st.selectbox("Choose a pre-built test template or write your own:", options=list(template_options.keys()))
default_prompt = template_options[selected_template]

test_prompt = st.text_area(
    "Describe the test case in plain English:", 
    value=default_prompt,
    height=100
)

if st.button("Generate Python Test"):
    if not GEMINI_API_KEY:
        st.error("Gemini API Key is missing.")
    else:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Updated to the latest model required by the API
            model = genai.GenerativeModel('gemini-3.8-flash')
            
            system_prompt = """
            You are a Salesforce QA automation expert writing Python code using the `simple-salesforce` library.
            CRITICAL RULES:
            1. Assume the connection object `sf` is ALREADY created. Do NOT write login code.
            2. Only output the raw Python code. Do not use markdown formatting (no ```python).
            3. Use Python `assert` statements to verify data was created or rules triggered properly.
            4. If an assert passes, use `print("[PASS] <description>")`.
            5. If an assert fails, use `print("[FAIL] <description>")`.
            6. Clean up (delete) any test records created at the very end of the script to keep staging clean.
            """
            
            with st.spinner("AI is writing the test script..."):
                response = model.generate_content(system_prompt + "\n\nUser Request: " + test_prompt)
                clean_code = response.text.replace("
