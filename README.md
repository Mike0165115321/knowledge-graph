# 🧠 Knowledge Graph - กราฟเชื่อมโยงข้อมูล

3D Cosmic Knowledge Graph Visualization สำหรับวิเคราะห์และแสดงผลความสัมพันธ์ของความรู้จากหนังสือต่างๆ

![3D Graph](https://img.shields.io/badge/3D-Graph-blue) ![Neo4j](https://img.shields.io/badge/Neo4j-Database-green) ![Next.js](https://img.shields.io/badge/Next.js-16-black)

## ✨ Features

- 🌌 **3D Neural Network Visualization** - กราฟ 3 มิติแบบ force-directed พร้อม glow effects
- ⚡ **Synapse Particles** - อนุภาควิ่งตามเส้นเชื่อมเหมือนกระแสประสาท
- 🔍 **ค้นหาได้** - ค้นหา nodes และซูมไปยังตำแหน่ง
- 📊 **3,297+ Nodes, 5,374+ Edges** - ข้อมูลจากหนังสือ 19+ เล่ม
- 🤖 **AI Debate System** - 3 AI Agents ถกเถียงสร้าง insights ใหม่

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ 
- **Python** 3.12+
- **Docker** (สำหรับ Neo4j)

### 1. Clone & Install

```bash
git clone https://github.com/Mike0165115321/knowledge-graph.git
cd knowledge-graph

# Frontend
npm install

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# หรือ venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Setup Environment

สร้างไฟล์ `backend/.env`:

```env
GOOGLE_API_KEYS=your_gemini_api_key_1,your_gemini_api_key_2
NEO4J_URI=bolt://localhost:7688
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

### 3. Start Neo4j Database

```bash
docker compose up -d
```

รอสักครู่ให้ Neo4j พร้อมใช้งาน (~30 วินาที)

### 4. Import Data (Optional)

ถ้าต้องการสร้างกราฟใหม่จาก JSONL:

```bash
cd backend
source venv/bin/activate
python scripts/build_graph.py
```

หรือ **import จาก exported data:**

```bash
# เปิด Neo4j Browser: http://localhost:7475
# แล้ว import จาก exports/graph_data.json
```

### 5. Start Servers

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

### 6. Open Browser

🌐 **Frontend:** http://localhost:3000
🔧 **API Docs:** http://localhost:8000/docs
🗄️ **Neo4j Browser:** http://localhost:7475

---

## 📁 Project Structure

```
knowledge-graph/
├── app/                    # Next.js pages
├── frontend/src/           # React components
│   └── components/GraphViz/
│       └── SunTzuGraph.tsx # 3D Graph Component
├── backend/
│   ├── app/
│   │   ├── agents/         # AI Agents (Predator, Guardian, Cartographer)
│   │   ├── core/           # Config, Neo4j client, Schemas
│   │   ├── extractors/     # Base graph extractor
│   │   └── main.py         # FastAPI server
│   ├── data/               # JSONL source files
│   └── scripts/            # Build scripts
├── exports/
│   └── graph_data.json     # Exported graph (3297 nodes, 5374 edges)
└── docker-compose.yml      # Neo4j container
```

---

## 🎮 Controls

| Action | Description |
|--------|-------------|
| **ลากเมาส์** | หมุนกราฟ 3D |
| **Scroll** | ซูมเข้า/ออก |
| **คลิก Node** | ดูรายละเอียด + ซูมไปที่ node |
| **ค้นหา** | พิมพ์ชื่อแล้วกด Enter |

---

## 🛠️ Tech Stack

- **Frontend:** Next.js 16, React, react-force-graph-3d, Three.js, TailwindCSS
- **Backend:** FastAPI, Python, LangChain
- **Database:** Neo4j (Docker)
- **AI:** Google Gemini 2.5 Flash

---

## 📚 Data Sources

หนังสือที่ใช้สร้าง Knowledge Graph:
- ตำราพิชัยสงคราม (The Art of War) - ซุนวู
- The 48 Laws of Power - Robert Greene
- Atomic Habits - James Clear
- Deep Work - Cal Newport
- จิตวิทยาสายดาร์ก
- และอีกมากมาย...

---

## 🤖 AI Agents

| Agent | Role |
|-------|------|
| **Predator** 🔴 | วิเคราะห์เทคนิคเชิงรุก การโจมตี |
| **Guardian** 🟢 | วิเคราะห์การป้องกัน จุดอ่อน |
| **Cartographer** 🔵 | สกัด nodes/edges จากการถกเถียง |

---

## 📄 License

MIT License

---

## 👤 Author

Mike - [@Mike0165115321](https://github.com/Mike0165115321)
