#!/bin/bash
# ============================================
#   Project Sun Tzu - Master Script
# ============================================
# วิธีใช้:
#   ./run.sh frontend   - รัน Frontend ดูกราฟ 3D (port 3000)
#   ./run.sh debate     - รัน AI Debate สร้างข้อมูล (Streamlit port 8501)
#   ./run.sh db         - เปิด Neo4j Browser (port 7475)
#   ./run.sh backup     - สร้าง Backup ฐานข้อมูล
#   ./run.sh restore    - กู้คืนจาก Backup
# ============================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

NEO4J_HOME="./neo4j-local/neo4j-community-5.26.0"
BACKUP_DIR="./backups"

# Ensure Neo4j is running
ensure_neo4j() {
    if ! pgrep -f "org.neo4j" > /dev/null; then
        echo -e "${YELLOW}🚀 Starting Neo4j...${NC}"
        $NEO4J_HOME/bin/neo4j start
        sleep 8
    fi
}

# ============================================
# Commands
# ============================================

cmd_frontend() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   🌐 Frontend - Graph Viewer (3D)    ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    
    ensure_neo4j
    
    # Start Backend API
    echo -e "${GREEN}🐍 Starting Backend API (port 8000)...${NC}"
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
    
    # Start Frontend
    echo -e "${GREEN}⚛️ Starting Frontend (port 3000)...${NC}"
    npm run dev &
    FRONTEND_PID=$!
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🌐 เปิด Browser: http://localhost:3000${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  กด Ctrl+C เพื่อหยุด${NC}"
    
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT
    wait
}

cmd_debate() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   🎭 AI Debate Arena (Streamlit)     ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    
    ensure_neo4j
    
    echo -e "${GREEN}🎭 Starting Debate UI (port 8501)...${NC}"
    cd backend
    source venv/bin/activate
    streamlit run app/debate_ui.py --server.port 8501
}

cmd_auto_debate() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   🤖 Auto Debate (Batch Mode)        ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    
    ensure_neo4j
    
    echo -e "${GREEN}🤖 Starting Auto Debate System...${NC}"
    cd backend
    source venv/bin/activate
    
    # Pass remaining arguments to the script
    shift 2>/dev/null || true
    python scripts/run_enhanced_debate.py "$@"
}

cmd_db() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   🗃️ Neo4j Database Browser          ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    
    ensure_neo4j
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🗃️ Neo4j Browser: http://localhost:7475${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  Login: neo4j / password${NC}"
    echo -e "${YELLOW}  Connect URL: neo4j://localhost:7688${NC}"
    echo ""
    
    # Keep running and show status
    $NEO4J_HOME/bin/neo4j status
    echo -e "${YELLOW}  กด Ctrl+C เพื่อหยุด Neo4j${NC}"
    
    trap "$NEO4J_HOME/bin/neo4j stop; exit" SIGINT
    tail -f $NEO4J_HOME/logs/neo4j.log
}

cmd_backup() {
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    
    echo -e "${GREEN}🔹 กำลังสร้าง Backup...${NC}"
    $NEO4J_HOME/bin/neo4j stop 2>/dev/null
    sleep 3
    
    BACKUP_FILE="$BACKUP_DIR/neo4j_backup_$TIMESTAMP.tar.gz"
    tar -czf "$BACKUP_FILE" -C "$NEO4J_HOME/data" .
    
    $NEO4J_HOME/bin/neo4j start
    echo -e "${GREEN}✅ Backup สำเร็จ: $BACKUP_FILE${NC}"
    ls -lh "$BACKUP_FILE"
}

cmd_restore() {
    LATEST=$(ls -t "$BACKUP_DIR"/neo4j_backup_*.tar.gz 2>/dev/null | head -1)
    
    if [ -z "$LATEST" ]; then
        echo -e "${RED}❌ ไม่พบไฟล์ backup${NC}"
        exit 1
    fi
    
    echo "📦 ใช้ backup: $LATEST"
    read -p "⚠️ ข้อมูลปัจจุบันจะถูกเขียนทับ! ยืนยัน? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $NEO4J_HOME/bin/neo4j stop 2>/dev/null
        sleep 3
        rm -rf "$NEO4J_HOME/data"/*
        tar -xzf "$LATEST" -C "$NEO4J_HOME/data"
        $NEO4J_HOME/bin/neo4j start
        echo -e "${GREEN}✅ กู้คืนสำเร็จ!${NC}"
    else
        echo "❌ ยกเลิก"
    fi
}

show_help() {
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   🧠 Project Sun Tzu - Help          ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo "Usage: ./run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  frontend   🌐 รัน Frontend ดูกราฟ 3D (port 3000)"
    echo "  debate       🎭 รัน AI Debate UI (port 8501)"
    echo "  auto-debate  🤖 รัน Auto Debate จาก topics.txt"
    echo "  db         🗃️ เปิด Neo4j Browser (port 7475)"
    echo "  backup     💾 สร้าง Backup ฐานข้อมูล"
    echo "  restore    🔄 กู้คืนจาก Backup ล่าสุด"
    echo "  help       📖 แสดงข้อความนี้"
    echo ""
}

# ============================================
# Main
# ============================================

case "$1" in
    frontend)   cmd_frontend ;;
    debate)       cmd_debate ;;
    auto-debate)  cmd_auto_debate "$@" ;;
    db)           cmd_db ;;
    backup)     cmd_backup ;;
    restore)    cmd_restore ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
