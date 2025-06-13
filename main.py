from flask import Flask, request, jsonify
import logging
import vertexai
from google.cloud import storage
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from neo4j import GraphDatabase, basic_auth
import json
import re
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
app.logger.setLevel(logging.DEBUG)

PROJECT = os.getenv("PROJECT")
LOCATION = os.getenv("LOCATION")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

vertexai.init(project=PROJECT, location=LOCATION)
app.logger.debug({"project_name":PROJECT,
                      "location": LOCATION,
                      "URI": NEO4J_URI,
                      "user_name":NEO4J_USER,
                      "password":NEO4J_PASSWORD})

model = GenerativeModel("gemini-2.0-flash-exp",generation_config=GenerationConfig(temperature=0.1))

app.logger.info("**** env setup is completed ****")

def get_pdf(bucket_name):
    storage_client = storage.Client(project=PROJECT)
    blobs = storage_client.list_blobs(bucket_name)

    blob_names = []
    for blob in blobs:
        blob_names.append(blob.name)

    return blob_names

@app.route("/env_check", methods=['GET'])
def test():
    app.logger.debug({"project_name":PROJECT,
                      "location": LOCATION,
                      "URI": NEO4J_URI,
                      "user_name":NEO4J_USER,
                      "password":NEO4J_PASSWORD})
    
    try:
        # Create a Neo4j driver instance
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # Test the connection by executing a simple query
        with driver.session() as session:
            result = session.run("RETURN 'Neo4j Connection Successful!' AS message")
            message = result.single()["message"]
        
        # Close the driver
        driver.close()

        # Log success and return the message
        app.logger.info("Neo4j connection successful.")
        return jsonify({"status": "success", "message": message})
    
    except Exception as e:
        app.logger.error(f"Neo4j connection failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/process_resumes', methods=['POST'])
def process_resumes():
    data = request.json
    bucket_name = data.get('bucket_name')
    name = get_pdf(bucket_name)
    pdf_path = []
    for file_name in name:
        pdf_file = Part.from_uri(
            uri="gs://" + bucket_name + "/" + file_name,
            mime_type="application/pdf",
        )
        pdf_path.append(pdf_file)
    graph = GraphDatabase.driver(uri=NEO4J_URI,auth=basic_auth(NEO4J_USER,NEO4J_PASSWORD))

    with open('push_knowledge_prompt.txt', 'r') as file:
        LLM1_prompt = file.read()

    # return jsonify({"info":LLM1_prompt}), 200
    with graph.session() as session:
        for pdf in pdf_path:
            app.logger.info("Info: starting with pdf")
            contents = [pdf,LLM1_prompt]
            response = model.generate_content(contents)
            query = response.text.split("```cypher")[-1].split('```')[0]
            session.run(query)
            app.logger.info("Info: pushed into NEO4J")

    app.logger.info("knowledge pushed Completed")
    return jsonify({"message": "Knowledge pushed"}), 200


@app.route('/fetching_schema',methods=['POST'])
def fetching_schema():
    graph = GraphDatabase.driver(uri=NEO4J_URI,auth=basic_auth(NEO4J_USER,NEO4J_PASSWORD))

    with graph.session() as session:
        result = session.run(""" MATCH (n)
        RETURN DISTINCT labels(n) AS Node_Labels, keys(n) AS Properties
        """)
        records = list(result)

    node_labels_list = []
    properties_list = []

    # session.close()
    for record in records:
        node_labels = record["Node_Labels"]
        properties = record["Properties"]

        node_labels_list.append(node_labels)
        properties_list.append(properties)


    a = model.start_chat()

    res = a.send_message(f"""here make the union on property on nodes lable 
                Node Lables: {node_labels_list}, Properties: {properties_list}
                only provide the node and property and nothing else""")


    SCHEMA_PLACEHOLDER = res.text.split("```")[1].split('json')[-1]
    return jsonify({"SCHEMA_PLACEHOLDER": SCHEMA_PLACEHOLDER}), 200


def fetch_data(user_query, search_type):
    schema_response = fetching_schema()
    with open('fetch_dataa_neo4j.txt', 'r') as file:
        LLM2_prompt = file.read()
    
    LLM2_prompt.replace("{schema_response}",str(schema_response) )
    model = GenerativeModel("gemini-2.0-flash-exp", generation_config=GenerationConfig(temperature=0.1), system_instruction=LLM2_prompt)

    chat = model.start_chat()
    res = chat.send_message(f"user_query:{user_query}, search_type:{search_type}")
    
    # Step 2: Use regular expressions to extract the JSON content
    json_pattern = r'\{.*\}'
    matches = re.findall(json_pattern, res.text, re.DOTALL)

    if matches:
        # Extracted JSON string
        json_content = matches[0]
        print("Extracted JSON Content:")
        print(json_content)
        
        # Parse the JSON content
        data = json.loads(json_content)

        # Extract Cypher and Python code
        cypher_code = data.get("cypher_code")
        python_code = data.get("python_code")

        print("\nCypher Code:")
        print(cypher_code)
        
        print("\nPython Code:")
        print(python_code)
        namespace = {}
        
        # return jsonify({"code":python_code})
        # Execute the Python code in the namespace
        exec(python_code, namespace)
        # exec(python_code,globals())

        graph = GraphDatabase.driver(uri=NEO4J_URI,auth=basic_auth(NEO4J_USER,NEO4J_PASSWORD))

        with graph.session() as session:
            result = session.run(cypher_code)
            # exec(python_code)
            result = list(result)
        res = namespace['parse_data'](result)
    return res

@app.route("/make_structured_output",methods=['POST'])
def make_structured_output():

    data = request.json
    user_query = data.get("user_query")
    search_type = data.get("search_type")
    
    res = fetch_data(user_query,search_type)
    
    with open('structure_output.txt', 'r') as file:
        LLM3_prompt = file.read()
    
    LLM3_prompt.replace("{user_query}",str(user_query))
    # return jsonify({"info", LLM3_prompt}, 200)
    model = GenerativeModel("gemini-2.0-flash-exp",generation_config=GenerationConfig(temperature=0.1),system_instruction=LLM3_prompt)

    chat = model.start_chat()
    history = chat.send_message(f"""below is the data:
                  {res}
                  """)

    return jsonify({"result":history.text},200)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=8080,threaded=True, use_reloader=True,debug=True)
