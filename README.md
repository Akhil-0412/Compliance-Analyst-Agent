# Compliance Analyst Agent 🛡️

**Agentic Compliance** is an autonomous regulatory oversight system that analyzes real-world scenarios against complex legal frameworks like GDPR, CCPA, and FDA regulations. It uses a sophisticated **LangGraph multi-agent architecture** combined with a robust **Next.js frontend** to provide real-time, explainable compliance risk assessments.

![Demo](https://img.shields.io/badge/Status-Active-brightgreen) ![License](https://img.shields.io/badge/License-MIT-blue)

## ✨ Core Features

1. **Agentic Reasoning Pipeline:**
   - **Guardrail Node:** Validates intent and prevents off-topic or malicious prompts.
   - **Hybrid Retrieval (RAG):** Uses FAISS to pull highly relevant regulatory clauses (e.g., specific GDPR Subsections) based on domain-specific logic.
   - **Clarification Multi-turn Flow:** Detects ambiguous queries and prompts the user with interactive follow-up questions before providing an analysis.
   - **Citation Validator:** Ensures the LLM's response accurately reflects the cited law without hallucination.
   - **Governance Gate:** Applies strict business rules and overrides (e.g., blocking high-risk actions).
2. **Server-Sent Events (SSE) Streaming:** Real-time visibility into the agent's thought process directly on the frontend.
3. **Structured Outputs:** Returns strongly-typed JSON containing risk levels, explicit legal references, and executive summaries.

---

## 🏗️ Architecture

The repository is modularized into two distinct services:

### 1. `backend/` (FastAPI + LangGraph + FAISS + Groq)
The intelligence engine. It builds and executes the compliance reasoning graph.
- **`agent/graph.py`**: The core StateGraph definition.
- **`agent/nodes.py`**: The individual reasoning steps (Retrieve, Clarify, LLM, Validate).
- **`backend/main.py`**: The FastAPI server exposing standard and SSE streaming endpoints.
- **`data/`**: Processed regulatory texts and embeddings.

### 2. `frontend/` (Next.js + Tailwind + Framer Motion)
The glassmorphic, interactive user interface.
- **Streaming UI:** Consumes the backend SSE stream to visualize node transitions in real-time.
- **Clarification Cards:** Interactive UI that prompts users for missing context.
- **Results Dashboard:** Displays risk levels (Low/Medium/High) with corresponding color mapping, the executive summary, and the structured regulatory mapping.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- [Groq API Key](https://console.groq.com/) (for fast LLM inference)

### 1. Start the Backend

```bash
cd backend
python -m venv .venv
# Activate the virtual environment:
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt

# Create a .env file and add your keys
echo "GROQ_API_KEY=your_key_here" > .env

# Run the FastAPI server
python app.py
```
*The backend runs on `http://127.0.0.1:8085`*

### 2. Start the Frontend

```bash
cd frontend
npm install

# Run the Next.js dev server
npm run dev
```
*The frontend runs on `http://localhost:3000`*

---

## 🔍 Example Scenarios to Try

- **Clear Scenario:** *"Is email considered personal data under GDPR?"*
  - The agent will immediately retrieve Article 4(1), synthesize the analysis, and return a Low/Medium risk assessment.

- **Ambiguous Scenario:** *"We lost patient data."*
  - The `clarify` node will detect missing context. The frontend will display follow-up questions like: *Was the data encrypted? How many records were lost?* Once answered, the pipeline resumes with enriched context.

---

## 🛠️ Tech Stack
- **AI/Agents**: LangGraph, FAISS, Instructor (Structured Outputs), Groq
- **Backend API**: FastAPI, Uvicorn, Python `asyncio`
- **Frontend**: Next.js (App Router), React, Tailwind CSS, Framer Motion, Lucide Icons

This project is built for high-stakes, explainable AI workflows where accurate citation and autonomous decision-making are critical.
