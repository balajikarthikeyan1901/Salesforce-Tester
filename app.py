import streamlit as st
import google.generativeai as genai
from simple_salesforce import Salesforce
import sys
import time
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
                # UPGRADE: Auto-retry loop to handle the 429 rate limit
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = model.generate_content(system_prompt + "\n\nUser Request: " + test_prompt)
                        # We use one line here so it doesn't cause a SyntaxError!
                        clean_code = response.text.replace("```python", "").replace("```", "").strip()
                        st.session_state.generated_code = clean_code
                        st.success("Test Script Generated!")
                        break # Success! Break out of the retry loop.
                        
                    except Exception as e:
                        if "429" in str(e) and attempt < max_retries - 1:
                            # If we hit the speed limit, warn the user and pause for 26 seconds
                            st.warning(f"Free tier speed limit reached. Pausing for 26 seconds to auto-retry (Attempt {attempt+1}/{max_retries})...")
                            time.sleep(26)
                        else:
                            # If it's a different error, or we ran out of retries, throw the error
                            raise e
                
        except Exception as e:
            st.error(f"Failed to generate code: {e}")

# --- 3. REVIEW, RUN & EXPORT LOGS ---
st.header("Step 2: Review & Run")
if st.session_state.generated_code:
    st.code(st.session_state.generated_code, language="python")
    
    if st.button("Validate & Run Automation"):
        if not username or not password:
            st.error("Please enter your Salesforce credentials in the sidebar.")
        else:
            try:
                st.info("Connecting to Staging Environment...")
                sf = Salesforce(username=username, password=password, security_token=security_token, domain='test')
                
                old_stdout = sys.stdout
                sys.stdout = my_stdout = StringIO()
                
                st.info("Executing test case...")
                local_variables = {'sf': sf}
                
                exec(st.session_state.generated_code, {}, local_variables)
                
                sys.stdout = old_stdout
                st.session_state.execution_logs = my_stdout.getvalue()
                
                st.success("Test Execution Complete!")
                
            except Exception as e:
                sys.stdout = old_stdout
                st.session_state.execution_logs = my_stdout.getvalue() + f"\n[CRITICAL ERROR] {e}"
                st.error("Test execution encountered an error.")

# --- 4. LOG EXPORT FEATURE ---
if st.session_state.execution_logs:
    st.text("Automation Logs:")
    st.code(st.session_state.execution_logs)
    
    st.download_button(
        label="Download Test Logs as .TXT",
        data=st.session_state.execution_logs,
        file_name="salesforce_test_execution_log.txt",
        mime="text/plain"
    )
