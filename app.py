import streamlit as st
import google.generativeai as genai
from simple_salesforce import Salesforce
import sys
from io import StringIO

st.title("Salesforce AI Test Automation")

# Fetch API key safely from Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = st.sidebar.text_input("Gemini API Key", type="password")

# --- 1. Sidebar for Salesforce Credentials ---
st.sidebar.header("Salesforce Credentials")
username = st.sidebar.text_input("Salesforce Username")
password = st.sidebar.text_input("Salesforce Password", type="password")
security_token = st.sidebar.text_input("Security Token", type="password")

if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""

# --- 2. AI Test Generator ---
st.header("Step 1: Generate Test Case")
test_prompt = st.text_area(
    "Describe the test case in plain English:", 
    placeholder="e.g., Create a new Account named 'Staging UI Test' with the industry 'Technology' and print the Account ID."
)

if st.button("Generate Python Test"):
    if not GEMINI_API_KEY:
        st.error("Gemini API Key is missing.")
    else:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            system_prompt = """
            You are a Salesforce automation expert writing Python code using the `simple-salesforce` library.
            CRITICAL RULES:
            1. Assume the connection object `sf` is ALREADY created. Do NOT write login code.
            2. Only output the raw Python code. Do not use markdown formatting (no ```python).
            3. Use print() statements to log successes, record IDs, or failures.
            """
            
            with st.spinner("Generating test script..."):
                response = model.generate_content(system_prompt + "\n\nUser Request: " + test_prompt)
                clean_code = response.text.replace("```python", "").replace("```", "").strip()
                st.session_state.generated_code = clean_code
                st.success("Code Generated Successfully!")
                
        except Exception as e:
            st.error(f"Failed to generate code: {e}")

# --- 3. Review and Run ---
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
                st.success("Connected to Salesforce!")
                
                old_stdout = sys.stdout
                sys.stdout = my_stdout = StringIO()
                
                st.info("Executing test case...")
                local_variables = {'sf': sf}
                exec(st.session_state.generated_code, {}, local_variables)
                
                sys.stdout = old_stdout
                st.success("Test Execution Complete!")
                st.text("Automation Logs:")
                st.code(my_stdout.getvalue())
                
            except Exception as e:
                st.error(f"Test Execution Failed: {e}")
