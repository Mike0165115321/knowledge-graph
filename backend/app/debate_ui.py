import streamlit as st
import time
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.enhanced_debate import get_enhanced_debate
from app.core.neo4j_client import neo4j_client
from streamlit_agraph import agraph, Node, Edge, Config

# Page Config
st.set_page_config(
    page_title="AI Debate Arena",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #c9d1d9; }
    .agent-card {
        padding: 15px; border-radius: 8px; border: 1px solid #30363d;
        background-color: #161b22; margin-bottom: 10px; font-size: 0.9em;
    }
    .attacker-card { border-left: 5px solid #ff4b4b; }
    .defender-card { border-left: 5px solid #00c853; }
    .analyst-card { border-left: 5px solid #29b6f6; background-color: #1f2937; }
    .thinking { color: #8b949e; font-style: italic; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("⚔️ Controls")
    topic_options = [
        "การควบคุมคนอื่นโดยไม่ให้รู้ตัว",
        "จุดอ่อนทางจิตวิทยาของมนุษย์",
        "กลยุทธ์การสร้างอิทธิพล",
        "การป้องกันตัวจากการถูกจัดการ",
        "ศิลปะแห่งการโน้มน้าว",
        "Custom Topic..."
    ]
    selected_topic = st.selectbox("Topic", topic_options)
    topic = st.text_input("Custom Topic", "ความเงียบคืออาวุธ") if selected_topic == "Custom Topic..." else selected_topic
    rounds = st.slider("Rounds", 1, 5, 2)
    delay = st.slider("Speed", 0.5, 5.0, 2.0)
    start_btn = st.button("🔥 Start Debate", type="primary", use_container_width=True)

# Initialize System with Spinner
@st.cache_resource(show_spinner="⏳ Loading 120 books into memory... (This happens once)")
def get_system():
    return get_enhanced_debate(data_dir="data")

# Load system before rendering main UI to ensure readiness
try:
    with st.spinner("🚀 Waking up AI Agents & Loading Library..."):
        system = get_system()
except Exception as e:
    st.error(f"❌ Failed to load system: {e}")
    st.stop()

st.title(f"🧠 AI Debate: {topic}")

# Layout: 3 Columns
col1, col2, col3 = st.columns([1, 1, 1.2])

with col1: st.markdown("### 🔴 Attacker")
with col2: st.markdown("### 🟢 Defender")
with col3: st.markdown("### 🔵 Analyst (Graph)")

# State management
if "messages" not in st.session_state: st.session_state.messages = []
if "graph_nodes" not in st.session_state: st.session_state.graph_nodes = []
if "graph_edges" not in st.session_state: st.session_state.graph_edges = []

# Helper to render messages
def render_message(msg):
    if msg['agent'] == "🔴 Attacker":
        with col1:
            st.markdown(f"<div class='agent-card attacker-card'>{msg['content']}</div>", unsafe_allow_html=True)
    elif msg['agent'] == "🟢 Defender":
        with col2:
            st.markdown(f"<div class='agent-card defender-card'>{msg['content']}</div>", unsafe_allow_html=True)
    elif msg['agent'] == "🔵 Analyst":
        with col3:
            st.markdown(f"<div class='agent-card analyst-card'><b>⚡ Insight:</b><br>{msg['content']}</div>", unsafe_allow_html=True)

# Render History
for msg in st.session_state.messages:
    render_message(msg)

# Persistent Graph Renderer
if st.session_state.graph_nodes:
    with col3:
        visual_nodes = []
        visual_edges = []
        type_color = {
            "concept": "#5e35b1", "technique": "#e53935",
            "risk": "#fb8c00", "defense": "#43a047", "book": "#1e88e5"
        }
        
        seen_ids = set()
        for n in st.session_state.graph_nodes:
            if n['id'] not in seen_ids:
                # Sanitize ID for visual (keep original for Label)
                safe_id = str(n['id']).replace(" ", "_")
                
                visual_nodes.append(Node(
                    id=safe_id, 
                    label=n['name'], 
                    size=15,
                    color=type_color.get(n.get('type', 'concept'), "#5e35b1"),
                    # Explicitly set image to None/Empty to prevent local file lookup
                    image=""
                ))
                seen_ids.add(n['id'])
        
        for e in st.session_state.graph_edges:
            visual_edges.append(Edge(
                source=str(e['source']).replace(" ", "_"), 
                target=str(e['target']).replace(" ", "_"), 
                label=e.get('type', ''), 
                color="#8b949e"
            ))
            
        config = Config(width=450, height=450, directed=True, physics=True, hierarchical=False)
        st.caption(f"🕸️ Nodes: {len(visual_nodes)} | Edges: {len(visual_edges)}")
        agraph(nodes=visual_nodes, edges=visual_edges, config=config)

# Logic
if "running" not in st.session_state:
    st.session_state.running = False

def start_debate_click():
    st.session_state.running = True
    st.session_state.messages = []
    st.session_state.graph_nodes = []
    st.session_state.graph_edges = []

if not st.session_state.running:
    # get_system() is cached and blocks until ready, so we can assume it's ready if we are here
    st.button("🔥 Start Debate", type="primary", use_container_width=True, on_click=start_debate_click)
else:
    if st.button("⏹️ Stop Debate", type="secondary", use_container_width=True):
        st.session_state.running = False
        st.rerun()

    with st.status("🤖 Debate in progress...", expanded=True) as status:
        try:
            for event in system.stream_debate(topic=topic, rounds=rounds, delay=delay):
                if not st.session_state.running: break
                
                if event['type'] == 'info':
                    st.toast(event['message'])
                
                elif event['type'] == 'thinking':
                    agent = event['agent']
                    msg = f"{event.get('message', 'Thinking...')} 💭"
                    if "Attacker" in agent:
                        with col1:
                            st.caption(msg)
                    elif "Defender" in agent:
                        with col2:
                            st.caption(msg)
                    elif "Analyst" in agent:
                        with col3:
                            st.caption(msg)
                
                elif event['type'] == 'message':
                    st.session_state.messages.append(event)
                    render_message(event)
                
                elif event['type'] == 'graph_update':
                    analyst_msg = {"agent": "🔵 Analyst", "content": f"Found {len(event['nodes'])} new nodes. Saving to Graph DB..."}
                    st.session_state.messages.append(analyst_msg)
                    render_message(analyst_msg)
                    
                    # 1. Update In-Memory State for UI
                    st.session_state.graph_nodes.extend(event['nodes'])
                    st.session_state.graph_edges.extend(event['edges'])
                    st.session_state.needs_graph_rerun = True
                    
                    # 2. Persist to Neo4j (Real Database)
                    try:
                        # Reconstruct objects from dicts (since event['nodes'] are dicts)
                        from app.core.schemas import GraphNode, GraphEdge, NodeType, EdgeType
                        
                        db_nodes = [GraphNode(**n) for n in event['nodes']]
                        db_edges = [GraphEdge(**e) for e in event['edges']]
                        
                        count_n = 0
                        for node in db_nodes:
                            neo4j_client.create_node(node)
                            count_n += 1
                            
                        count_e = 0
                        for edge in db_edges:
                            neo4j_client.create_edge(edge)
                            count_e += 1
                            
                        print(f"✅ Saved to Neo4j: {count_n} nodes, {count_e} edges")
                        st.toast(f"💾 Saved {count_n} nodes to Neo4j DB!")
                        
                    except Exception as e:
                        print(f"❌ Failed to save to Neo4j: {e}")
                        st.error(f"DB Save Error: {e}")
            
            st.session_state.running = False
            status.update(label="✅ Completed!", state="complete", expanded=False)
            
        except Exception as e:
            st.error(f"Error during debate: {e}")
            st.session_state.running = False

# Force update graph if needed
if st.session_state.get("needs_graph_rerun"):
    st.session_state.needs_graph_rerun = False
    st.rerun()
