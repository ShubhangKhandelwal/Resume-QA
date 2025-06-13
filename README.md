## How to Set-up:
## 1. install NEO4J, and make a DB
## 2. make a USER and set PASS_WORD
## 3. make changes in .env file
## 4. run the server: "python main.py"
## 5. run the streamlit: "streamlit run litapp.py"

# json related to api used
here search has 2 types: "quick_search", "full_search"
## make structured output
{

    "user_query":"which candidates have exposure in java",

    "search_type": "quick search"

}
## process resume

{

    "bucket_name" : "resume-testing-1"

}
