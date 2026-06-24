
# 🧠 AuditPRO‑Edge: AI-Powered Smart Contract Auditing Platform

[![CI](https://github.com/Mowafag100/AuditPRO-Edge/actions/workflows/ci.yml/badge.svg)](https://github.com/Mowafag100/AuditPRO-Edge/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138+-green)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-purple)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A fully integrated platform for analyzing legal and smart contracts using on-device AI (Llama3) with RAG, LangGraph Agents, real-time monitoring, and interactive chat.**

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **🔍 Intelligent Analysis** | Uses local Llama3 (via Ollama) to extract risks, summaries, and actionable recommendations from PDF contracts. |
| **🧠 RAG (Retrieval-Augmented Generation)** | Retrieves relevant context from a vector database (ChromaDB) to improve the accuracy and depth of the analysis. |
| **🤖 LangGraph Agents** | Multi-step agent pipeline: retrieves context → analyzes the contract → generates structured output. |
| **📊 Enterprise Monitoring** | Exposes `/health` and `/metrics` endpoints with Prometheus-compatible metrics. |
| **📝 Structured Logging** | JSON-formatted logs using `structlog` for easy integration with logging pipelines. |
| **🧪 Evaluation Framework** | Evaluates precision, recall, and F1-score of the analysis against ground-truth references. |
| **🐳 One-Click Deployment** | Fully containerized with Docker Compose — runs all services (Ollama, ChromaDB, PostgreSQL, Redis, FastAPI, Next.js) with a single command. |
| **⚙️ CI/CD Pipeline** | GitHub Actions automates linting, testing, building, and Docker image creation. |

---

## 🏗️ Technology Stack

| Component | Technology |
| :--- | :--- |
| **Backend** | FastAPI + Python 3.11 |
| **Frontend** | Next.js 16 (React + Turbopack) |
| **Relational Database** | PostgreSQL (production) + SQLite (development) |
| **Vector Database** | ChromaDB (for RAG) |
| **AI Model** | Ollama + Llama3 8B |
| **Agent Framework** | LangGraph |
| **Monitoring** | Prometheus (`/metrics`) |
| **Logging** | structlog (JSON logs) |
| **CI/CD** | GitHub Actions |
| **Containerization** | Docker + Docker Compose |

---

## 🚀 Quick Start (For Developers)

### Prerequisites
- Docker + Docker Compose installed
- Git
- 8GB+ RAM (16GB recommended)

### 1. Clone the repository
```bash
git clone https://github.com/Mowafag100/AuditPRO-Edge.git
cd AuditPRO-Edge
2. Start all services with Docker Compose
bash
docker compose up -d
3. Pull the Llama3 model (first time only)
bash
docker compose exec ollama ollama pull llama3
4. Open the frontend
Visit http://localhost:3000

5. Test the API (optional)
bash
# Get an authentication token
TOKEN=$(curl -s -X POST http://localhost:8090/login | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Analyze a PDF contract
curl -X POST http://localhost:8090/analyze-contract \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your_contract.pdf"
📷 Screenshots
<div align="center"> <h3>🏠 Main Interface & File Upload</h3> <img width="80%" alt="Main interface and file upload" src="https://github.com/user-attachments/assets/31bb3299-ba5f-40d4-bec3-02587cb59ffb" /> <br/><br/> <h3>📊 Analysis Results & Risk Gauge</h3> <img width="80%" alt="Analysis results with risk gauge, risks, recommendations, and chat" src="https://github.com/user-attachments/assets/80554f3e-04e6-401a-b0ae-84f696b1f5bc" /> <br/><br/> <p><em>Detailed risk analysis with interactive risk gauge, structured risks, actionable recommendations, and integrated AI chat.</em></p> </div>
📂 Project Structure
text
AuditPRO-Edge/
├── agents/
│   └── audit_graph.py          # LangGraph agent definition
├── src/
│   ├── logging_config.py       # structlog configuration
│   └── evaluation.py           # Evaluation framework
├── tests/
│   └── test_api.py             # Unit tests for CI
├── .github/workflows/
│   └── ci.yml                  # GitHub Actions pipeline
├── main.py                     # FastAPI entry point
├── docker-compose.yml          # Multi-service orchestration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
🧪 Testing & Evaluation
Unit tests: pytest tests/

Quality evaluation: Use the /evaluate endpoint with a reference text.

Performance monitoring: http://localhost:8090/metrics (Prometheus compatible).

🤝 Contributing
We welcome contributions! Please follow these steps:

Fork the repository.

Create a new branch (git checkout -b feature/amazing-feature).

Make your changes and add tests.

Push to your branch (git push origin feature/amazing-feature).

Open a Pull Request.

📜 License
This project is licensed under the MIT License.

📧 Contact
Developer: Mowafag Fawzy

Email: mowafagfawzy@gmail.com

GitHub: Mowafag100

🌟 If you like this project, don't forget to give it a star on GitHub!
