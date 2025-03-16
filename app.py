from flask import Flask, jsonify, render_template, request
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types
import pandas as pd
import faiss
import json
import xml.etree.ElementTree as ET
import csv
import io

# sys_ins = "Your name is Geeko. You are a polite and helpful assistant.\
# Keep responses concise, under 50 characters."

global role, chat, test_assitant, bot
role = "bot"
chat = None
faiss_index =""
test_cases = ""
client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

test_assitant = "# Geeko 2.0 - System Instruction\
You are **Geeko 2.0**, a helpful testing assistant responsible for test cases of the *uploaded* application.\
## Behavior Guidelines\
- Respond politely to general greetings.  \
- Maintain professionalism and clarity in responses.  \
\
## Response Rules\
1. **If a user asks what you can do**, reply:  \
   *\"I can help you with understanding testcases you have upload.\"*  \
2. **When given a query**, review the provided *TestLink* test cases (`results`) and respond based on the most relevant ones.  \
3. **Do not mention test case IDs** unless explicitly requested by the user.  \
4. **If the user provides a specific test case ID** and asks for an explanation, explain *only that test case*."

bot = "# Geeko 2.0 - System Instruction\
You are **Geeko 2.0**, a helpful assitant\
## Behavior Guidelines\
- Respond politely to general greetings.  \
- Maintain professionalism and clarity in responses."

def create_new_chat(role):
    global chat
    chat = client.chats.create(
        model="gemini-2.0-flash", 
        config=types.GenerateContentConfig(system_instruction=role)
        )
    
def xml_to_csv(xml_file, csv_file):
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Define base headers (non-step fields)
    base_headers = [
        "internalid", "name", "node_order", "externalid", "version", "summary",
        "preconditions", "execution_type", "importance"
    ]

    # Determine the maximum number of steps in any testcase
    max_steps = max(len(testcase.find('steps')) for testcase in root.findall('testcase') if testcase.find('steps') is not None)

    # Generate step headers dynamically
    step_headers = []
    for i in range(max_steps):
        step_headers.extend([
            f"steps/step/{i}/step_number",
            f"steps/step/{i}/actions",
            f"steps/step/{i}/expectedresults",
            f"steps/step/{i}/execution_type"
        ])

    # Combine base headers and step headers
    headers = base_headers + step_headers

    # Open the CSV file for writing
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()

        # Iterate through each <testcase>
        for testcase in root.findall('testcase'):
            # Extract base data
            testcase_data = {
                "internalid": testcase.get('internalid'),
                "name": testcase.get('name'),
                "node_order": testcase.findtext('node_order', '').strip(),
                "externalid": testcase.findtext('externalid', '').strip(),
                "version": testcase.findtext('version', '').strip(),
                "summary": testcase.findtext('summary', '').strip(),
                "preconditions": testcase.findtext('preconditions', '').strip(),
                "execution_type": testcase.findtext('execution_type', '').strip(),
                "importance": testcase.findtext('importance', '').strip(),
            }

            # Extract step data
            steps = testcase.find('steps')
            if steps is not None:
                for i, step in enumerate(steps.findall('step')):
                    testcase_data.update({
                        f"steps/step/{i}/step_number": step.findtext('step_number', '').strip(),
                        f"steps/step/{i}/actions": step.findtext('actions', '').strip(),
                        f"steps/step/{i}/expectedresults": step.findtext('expectedresults', '').strip(),
                        f"steps/step/{i}/execution_type": step.findtext('execution_type', '').strip(),
                    })
                # Fill in missing steps with empty values
                for i in range(len(steps.findall('step')), max_steps):
                    testcase_data.update({
                        f"steps/step/{i}/step_number": "",
                        f"steps/step/{i}/actions": "",
                        f"steps/step/{i}/expectedresults": "",
                        f"steps/step/{i}/execution_type": "",
                    })
            else:
                # If no steps, fill all step columns with empty values
                for i in range(max_steps):
                    testcase_data.update({
                        f"steps/step/{i}/step_number": "",
                        f"steps/step/{i}/actions": "",
                        f"steps/step/{i}/expectedresults": "",
                        f"steps/step/{i}/execution_type": "",
                    })

            # Write the row to the CSV
            writer.writerow(testcase_data)

    print(f"CSV file '{csv_file}' has been created successfully.")

# Load Embedding Model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Load and Process Test Cases from TestLink CSV
def load_test_cases(csv_file):
    df = pd.read_csv(csv_file)

    mandatory_fields = ["externalid", "summary", "preconditions"]
    for field in mandatory_fields:
        if field not in df.columns:
            raise ValueError(f"Mandatory field {field} is missing in the CSV file.")
        
    # Combine all steps and expected results into a single text field
    def combine_steps(row):
        steps_text = []
        for i in range(11):  # Assuming max 11 steps (steps/step/0 to steps/step/10)
            action_col = f"steps/step/{i}/actions"
            expected_col = f"steps/step/{i}/expectedresults"
            
            if action_col in row and expected_col in row:
                action = str(row[action_col]) if pd.notna(row[action_col]) else ""
                expected = str(row[expected_col]) if pd.notna(row[expected_col]) else ""
                steps_text.append(f"Step {i+1}: {action} -> Expected: {expected}")
        
        return " \n ".join(steps_text)    
    df["combined_text"] = df["externalid"].astype(str) + " " + df["summary"] + " " + df["preconditions"] + " " + df.apply(combine_steps, axis=1)
    return df

def embed_texts(texts):
    return np.array(embedding_model.encode(texts))
    
# Initialize FAISS Index
def create_faiss_index(embeddings):
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index
    
def set_up_knowledge_base():
    global faiss_index, test_cases
    # Load and Process Test Cases
    try:
        test_cases = load_test_cases("./static/knowledge_base.csv")
        embeddings = embed_texts(test_cases["combined_text"].tolist())
        faiss_index = create_faiss_index(embeddings)
    except:
        return False
    return True

app = Flask(__name__)


@app.route('/',methods=["GET","POST"])
def Chat():
    global role, chat, test_assitant, bot, faiss_index, test_cases
    if request.method == "GET":
        return render_template('chatbot.html', response="")
    else:
        response_text =""
        user_input = request.json["message"]
        test_assist = request.json["testAssistance"]
        
        if test_assist and role != "test_assitant":
            role = "test_assitant"
            create_new_chat(test_assitant)
        elif not test_assist and role != "bot":
            role = "bot"
            create_new_chat(bot)
            
        if user_input:
            if request.json["testAssistance"]:                 
                
                query_embedding = embedding_model.encode([user_input])
                try:
                    D, I = faiss_index.search(np.array(query_embedding), k=5)
                    results = test_cases.iloc[I[0]][["externalid", "summary", "preconditions", "combined_text"]].to_dict(orient="records")
                    user_txt = json.dumps({"query": user_input, "results": results})
                    response = chat.send_message(user_txt)
                    response_text = response.text
                except:
                    response_text = "Please add a Valid XML file and continue"
                
            else:
                response = chat.send_message(user_input)
                response_text = response.text
                
        else:
            response_text = "No input provided."

        return jsonify({"response": response_text})

@app.route('/file', methods=["POST"])
def handle_file_upload():
    data = request.json
    if data and 'file' in data:
        xml_content = data['file']  # Raw CSV string

        xml_content = io.StringIO(data['file'])
        try:
            xml_to_csv(xml_content, "./static/knowledge_base.csv")
            print("File saved")
            var = set_up_knowledge_base()
            
            if var:
                return jsonify({"response": "File uploaded successfully."})
            else:
                return jsonify({"response": "Mandatory fields are missing. Please import testlink exported XML file."}), 400
        except:
            print("Failed")
            return jsonify({"response": "Mandatory fields are missing. Please import testlink exported XML file."}), 400

    else:
        return jsonify({"response": "File upload failed."}), 400

create_new_chat(role)
app.run(debug=True)  # Start the server