#!/bin/bash

echo "🚀 Starting AuditPRO Platform Setup..."

# 1. Create Python Virtual Environment
echo "📦 Setting up Python Environment..."
python3 -m venv venv
source venv/bin/activate

# 2. Install Backend Dependencies
echo "📥 Installing Backend Dependencies..."
pip install fastapi uvicorn pdfplumber openai pyjwt passlib python-multipart

# 3. Install Frontend Dependencies
echo "📥 Installing Frontend Dependencies..."
npm install

# 4. Initialize Database
echo "🗄️ Initializing SQLite Database..."
python3 -c "import main; main.init_db(); print('Database Ready!')"

echo "✅ Setup Complete!"
echo "To start the platform, run: ./run.sh"
