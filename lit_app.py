import streamlit as st
import requests

# Streamlit app title
st.title("Resume Processor and Q&A System")

# User selection buttons
option = st.radio(
    "Choose an Action:",
    ["Process Resumes", "Q&A"]
)

# Process Resume Logic
if option == "Process Resumes":
    st.header("Process Resumes")
    bucket_name = st.text_input("Enter Bucket Name (e.g., 'resume-testing-1')", "")
    
    if st.button("Submit"):
        if bucket_name:
            # Construct JSON payload
            json_payload = {"bucket_name": bucket_name}
            
            # Send request to API
            api_url = "http://localhost:8080/process_resumes"  # Replace with your API endpoint
            try:
                response = requests.post(api_url, json=json_payload)
                if response.status_code == 200:
                    st.success(f"Success: {response.json()['message']}")
                else:
                    st.error(f"Error: {response.json().get('message', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a bucket name.")

# Q&A Logic
if option == "Q&A":
    st.header("Q&A")
    
    # Dropdown for search type
    search_type = st.selectbox(
        "Choose Search Type:",
        options=["full_search", "quick_search"],
        index=0
    )
    
    # User query input
    user_query = st.text_area("Enter your Query", "")
    
    if st.button("Search"):
        if user_query:
            # Construct JSON payload
            json_payload = {
                "user_query": user_query,
                "search_type": search_type
            }
            
            # Send request to API
            api_url = "http://localhost:8080/make_structured_output"  # Replace with your API endpoint
            try:
                response = requests.post(api_url, json=json_payload)
                if response.status_code == 200:
                    st.success("Search completed successfully.")
                    st.json(response.json())  # Display response JSON
                else:
                    st.error(f"Error: {response.json().get('message', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a query.")
