#!/bin/bash
cd backend
source venv/bin/activate
echo "🚀 Starting AI Debate Arena..."
streamlit run app/debate_ui.py --server.port 8501
