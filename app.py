from flask import Flask, jsonify, render_template, request
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types
import pandas as pd
import faiss
import json


# sys_ins = "Your name is Geeko. You are a polite and helpful assistant.\
# Keep responses concise, under 50 characters."

sys_ins = "# Geeko 2.0 - System Instruction\
You are **Geeko 2.0**, a helpful testing assistant responsible for explaining **autocomplete** and **geocoding** test cases of the *Nuwa* application.\
## Behavior Guidelines\
- Respond politely to general greetings.  \
- Maintain professionalism and clarity in responses.  \
- Only discuss *autocomplete* and *geocoding* test cases.\
\
## Response Rules\
1. **If a user asks what you can do**, reply:  \
   *\"I can help you understand autocomplete and geocoding test cases of Nuwa.\"*  \
2. **When given a query**, review the provided *TestLink* test cases (`results`) and respond based on the most relevant ones.  \
3. **Do not mention test case IDs** unless explicitly requested by the user.  \
4. **If the user provides a specific test case ID** and asks for an explanation, explain *only that test case*."


client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
chat = client.chats.create(
        model="gemini-2.0-flash", 
        config=types.GenerateContentConfig(system_instruction=sys_ins)
        )

# Load Embedding Model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Load and Process Test Cases from TestLink CSV
def load_test_cases(csv_file):
    df = pd.read_csv(csv_file)
    
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

# Load and Process Test Cases
test_cases = load_test_cases("./static/knowledge_base.csv")
embeddings = embed_texts(test_cases["combined_text"].tolist())
faiss_index = create_faiss_index(embeddings)

app = Flask(__name__)

@app.route('/',methods=["GET","POST"])
def Chat():
    if request.method == "GET":
        return render_template('chatbot.html', response="")
    else:
        user_input = request.json["message"]
        if user_input:
            query_embedding = embedding_model.encode([user_input])
            D, I = faiss_index.search(np.array(query_embedding), k=5)
            results = test_cases.iloc[I[0]][["externalid", "summary", "preconditions", "combined_text"]].to_dict(orient="records")
            user_txt = json.dumps({"query": user_input, "results": results})
            response = chat.send_message(user_txt)
            response_text = response.text
        else:
            response_text = "No input provided."

        return jsonify({"response": response_text})
    
app.run(debug=True)  # Start the server