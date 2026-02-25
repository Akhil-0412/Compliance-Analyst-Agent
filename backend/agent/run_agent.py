import os
import json
import sys

# Ensure the script can see all subfolders correctly
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from retrieval.indexer import ClauseIndexer
from agent.analyst import ComplianceAgent

def main():
    # 1. Get the directory where THIS script (run_agent.py) lives
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Get the PROJECT ROOT (one level up from 'agent')
    project_root = os.path.dirname(current_script_dir)
    
    # 3. Construct the path to the data folder in the root
    data_path = os.path.join(project_root, "data", "processed", "gdpr_structured.json")
    
    # --- DEBUG PRINT: Let's see if we got it right this time ---
    print(f"📂 Resolved Data Path: {data_path}")
    
    if not os.path.exists(data_path):
        print(f"❌ ERROR: Still can't find the file at the path above!")
        return
    # ---------------------------------------------------------

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Build the Index (with Title Injection for precision)
    indexer = ClauseIndexer()
    texts = []
    metadata = []
    
    for a in data['articles']:
        title = a.get('title', 'GDPR Regulation')
        for c in a['clauses']:
            texts.append(f"Article {a['article_id']} - {title}: {c['text']}")
            metadata.append({
                "article_id": str(a['article_id']),
                "clause_id": c['clause_id'],
                "text": c['text'],
                "clause_type": c.get('clause_type', 'other')
            })
            
    indexer.build(texts, metadata)

    # 2. Run the Compliance Agent
    agent = ComplianceAgent(indexer, data_path)
    question = "What is the maximum fine if I fail to implement Privacy by Design?"
    
    print(f"\n🤔 Question: {question}")
    print("-" * 50)
    print(agent.analyze(question))

if __name__ == "__main__":
    main()