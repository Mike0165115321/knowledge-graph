#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Project Sun Tzu - Execution Script  ${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. Check Directories
if [ ! -d "backend/venv" ]; then
    echo -e "${RED}Python venv not found! Creating...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# 2. Start Database (Neo4j)
echo -e "${GREEN}Checking Neo4j Container...${NC}"
if [ ! "$(docker ps -q -f name=neo4j)" ]; then
    if [ "$(docker ps -aq -f name=neo4j)" ]; then
        echo "Starting existing Neo4j container..."
        docker start neo4j
    else
        echo "Creating new Neo4j container..."
        docker-compose up -d neo4j
    fi
    echo "Waiting for Neo4j to be ready..."
    sleep 10
fi

# 3. Reset Data Option
read -p "Do you want to RESET the database (Delete all data)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Resetting Database...${NC}"
    cd backend
    source venv/bin/activate
    # Use 'echo 'y' to auto-confirm the python script prompt
    echo 'y' | python scripts/reset_db.py
    
    echo -e "${GREEN}Importing Base Data (Fast Import)...${NC}"
    python scripts/import_base.py
    cd ..
else
    echo "Skipping reset."
fi

# 4. Start Services
echo -e "${GREEN}Starting Backend & Frontend...${NC}"

# Kill existing ports if any (Optional, be careful)
# fuser -k 8000/tcp
# fuser -k 3000/tcp

# Function to handle cleanup on exit
cleanup() {
    echo -e "${RED}Stopping services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID
    exit
}
trap cleanup SIGINT

# Start Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend running (PID: $BACKEND_PID)"

# Start Frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend running (PID: $FRONTEND_PID)"

# Wait
wait
