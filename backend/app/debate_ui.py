import streamlit as st
import time
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.enhanced_debate import get_enhanced_debate
from app.core.neo4j_client import neo4j_client
from app.core.debate_history import (
    save_debate, get_all_debates, get_debate, search_debates, delete_debate, get_stats as get_history_stats
)
from app.core import tts
from streamlit_agraph import agraph, Node, Edge, Config

# ============================================
# TTS Helper
# ============================================

def render_message_with_tts(agent, content, key_prefix, auto_play=False):
    """
    Renders a message with optional TTS. If auto_play=True, generates and plays immediately.
    """
    # Determine style based on agent
    style_class = "agent-card"
    label = agent
    if "Attacker" in agent or "Time" in agent:
        style_class = "agent-card attacker-card"
        label = "🔴 ทาม (Time)"
    elif "Defender" in agent or "Ann" in agent:
        style_class = "agent-card defender-card"
        label = "🟢 แอน (Ann)"
    elif "Strategist" in agent or "Mike" in agent:
        style_class = "agent-card strategist-card"
        label = "🟣 ไมค์ (Mike)"
    
    # Display message card
    st.markdown(f"<div class='{style_class}'><b>{label}</b><br>{content}</div>", unsafe_allow_html=True)
    
    # Auto-play mode: generate and play immediately
    if auto_play:
        audio_bytes = tts.get_audio_for_agent(content, agent)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
    else:
        # Manual button mode
        btn_key = f"tts_{key_prefix}"
        if st.button("🔊 ฟังเสียง", key=btn_key):
            audio_bytes = tts.get_audio_for_agent(content, agent)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3", start_time=0)

# Page Config
st.set_page_config(
    page_title="สังเวียน AI Debate",
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
    .strategist-card { border-left: 5px solid #9c27b0; }
    .topic-card {
        padding: 10px; border-radius: 6px; border: 1px solid #30363d;
        background-color: #21262d; margin: 5px 0;
    }
    .topic-done { border-left: 4px solid #00c853; }
    .topic-current { border-left: 4px solid #ffc107; background-color: #2d3748; }
    .topic-pending { border-left: 4px solid #6b7280; }
    .history-card {
        padding: 12px; border-radius: 8px; border: 1px solid #30363d;
        background-color: #161b22; margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# Helper Functions
# ============================================

TOPICS_FILE = Path("scripts/topics.txt")
COMPLETED_FILE = Path("scripts/completed_topics.txt")

def load_topics():
    if not TOPICS_FILE.exists():
        return []
    topics = []
    with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                topics.append(line)
    return topics

def load_completed():
    if not COMPLETED_FILE.exists():
        return set()
    with open(COMPLETED_FILE, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}

def save_completed(topic):
    with open(COMPLETED_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{topic}\n")

def clear_completed():
    if COMPLETED_FILE.exists():
        COMPLETED_FILE.unlink()

# Initialize System
@st.cache_resource(show_spinner="⏳ กำลังโหลดหนังสือ 120 เล่ม...")
def get_system():
    return get_enhanced_debate(data_dir="data")

try:
    with st.spinner("🚀 กำลังปลุก AI Agents..."):
        system = get_system()
except Exception as e:
    st.error(f"❌ Failed to load system: {e}")
    st.stop()

# ============================================
# SIDEBAR: Settings
# ============================================

with st.sidebar:
    st.header("⚙️ ตั้งค่า TTS")
    
    if "tts_auto_play" not in st.session_state:
        st.session_state.tts_auto_play = False
    
    st.session_state.tts_auto_play = st.toggle(
        "🔊 เปิดเสียงอัตโนมัติ",
        value=st.session_state.tts_auto_play,
        help="เมื่อเปิด AI จะพูดออกเสียงอัตโนมัติเมื่อสร้างข้อความเสร็จ"
    )
    
    if st.session_state.tts_auto_play:
        st.success("🎙️ โหมดคุยสด: เสียงจะเล่นอัตโนมัติ")
    else:
        st.info("🔇 โหมดเงียบ: กดปุ่มเพื่อฟังเสียง")

# ============================================
# LAYOUT: Tabs
# ============================================

tab1, tab2, tab3, tab4 = st.tabs(["🎭 หัวข้อเดียว", "📋 รันอัตโนมัติ", "📖 ประวัติสนทนา", "📊 กราฟความรู้"])

# ============================================
# TAB 1: Single Topic
# ============================================
with tab1:
    st.header("🎭 Debate หัวข้อเดียว")
    
    topic = st.text_input("หัวข้อ", "ความเงียบคืออาวุธ", key="single_topic")
    col_r, col_d = st.columns(2)
    with col_r:
        rounds = st.slider("จำนวนรอบ", 1, 5, 2, key="single_rounds")
    with col_d:
        delay = st.slider("หน่วงเวลา (วินาที)", 1, 10, 3, key="single_delay")
    
    if "single_running" not in st.session_state:
        st.session_state.single_running = False
    if "single_messages" not in st.session_state:
        st.session_state.single_messages = []
    
    if not st.session_state.single_running:
        if st.button("🔥 เริ่ม Debate", type="primary", key="single_start"):
            st.session_state.single_running = True
            st.session_state.single_messages = []
            st.rerun()
    else:
        if st.button("⏹️ หยุด", key="single_stop"):
            st.session_state.single_running = False
            st.rerun()
        
        col1, col2 = st.columns(2)
        node_count = 0
        edge_count = 0
        
        with st.status("🤖 กำลัง Debate...", expanded=True):
            try:
                for event in system.stream_debate(topic=topic, rounds=rounds, delay=delay):
                    if not st.session_state.single_running:
                        break
                    
                    if event['type'] == 'message':
                        st.session_state.single_messages.append(event)
                        render_message_with_tts(event['agent'], event['content'], f"single_{len(st.session_state.single_messages)}", auto_play=st.session_state.tts_auto_play)
                    
                    elif event['type'] == 'graph_update':
                        node_count += len(event['nodes'])
                        edge_count += len(event['edges'])
                        
                        from app.core.schemas import GraphNode, GraphEdge
                        for n in event['nodes']:
                            try: neo4j_client.create_node(GraphNode(**n))
                            except: pass
                        for e in event['edges']:
                            try: neo4j_client.create_edge(GraphEdge(**e))
                            except: pass
                        
                        st.toast(f"💾 บันทึก {len(event['nodes'])} nodes!")
                
                # Save to history
                if st.session_state.single_messages:
                    save_debate(
                        topic=topic,
                        messages=st.session_state.single_messages,
                        rounds=rounds,
                        node_count=node_count,
                        edge_count=edge_count
                    )
                    st.toast("📖 บันทึกประวัติแล้ว!")
                
                st.session_state.single_running = False
                st.success("✅ Debate เสร็จสิ้น!")
                
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.single_running = False
    
    if st.session_state.single_messages:
        st.subheader("📜 บทสนทนา")
        for i, msg in enumerate(st.session_state.single_messages):
            with st.expander(msg['agent'], expanded=False):
                render_message_with_tts(msg['agent'], msg['content'], f"history_single_{i}")

# ============================================
# TAB 2: Auto Queue
# ============================================
with tab2:
    st.header("📋 รัน Debate อัตโนมัติ")
    
    topics = load_topics()
    completed = load_completed()
    pending = [t for t in topics if t not in completed]
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("📄 ทั้งหมด", len(topics))
    col_b.metric("✅ เสร็จแล้ว", len(completed))
    col_c.metric("⏳ รอดำเนินการ", len(pending))
    
    with st.expander("⚙️ ตั้งค่า"):
        delay_between = st.slider("หน่วงเวลาระหว่างหัวข้อ (วินาที)", 10, 120, 30, key="auto_delay")
        auto_rounds = st.slider("จำนวนรอบต่อหัวข้อ", 1, 3, 2, key="auto_rounds")
        if st.button("🗑️ รีเซ็ตความคืบหน้า"):
            clear_completed()
            st.rerun()
    
    if "auto_running" not in st.session_state:
        st.session_state.auto_running = False
    if "auto_current" not in st.session_state:
        st.session_state.auto_current = None
    
    if not st.session_state.auto_running:
        if pending:
            if st.button("🚀 เริ่มรันอัตโนมัติ", type="primary", use_container_width=True):
                st.session_state.auto_running = True
                st.rerun()
        else:
            st.success("🎉 ทุกหัวข้อเสร็จสิ้นแล้ว!")
    else:
        if st.button("⏹️ หยุดคิว", type="secondary", use_container_width=True):
            st.session_state.auto_running = False
            st.rerun()
        
        progress = st.progress(0)
        status_text = st.empty()
        
        # Single container for conversation (works better with streaming)
        st.markdown("---")
        st.subheader("💬 สนทนาสด")
        conversation_area = st.container()
        
        st.markdown("---")
        log_area = st.container()
        
        for i, topic in enumerate(pending):
            if not st.session_state.auto_running:
                break
            
            st.session_state.auto_current = topic
            progress.progress(i / len(pending))
            status_text.markdown(f"**[{i+1}/{len(pending)}]** 🎭 **{topic}**")
            
            messages = []
            node_count = 0
            edge_count = 0
            
            # Show topic header in conversation
            with conversation_area:
                st.markdown(f"### 🎯 {topic}")
            
            try:
                for event in system.stream_debate(topic=topic, rounds=auto_rounds, delay=3):
                    if not st.session_state.auto_running:
                        break
                    
                    if event['type'] == 'message':
                        messages.append(event)
                        agent = event['agent']
                        content = event['content']
                        
                        # Display in conversation area (sequential)
                        with conversation_area:
                            render_message_with_tts(agent, content, f"auto_{i}_{len(messages)}", auto_play=st.session_state.tts_auto_play)
                    
                    elif event['type'] == 'graph_update':
                        nodes = event['nodes']
                        edges = event['edges']
                        node_count += len(nodes)
                        edge_count += len(edges)
                        
                        from app.core.schemas import GraphNode, GraphEdge
                        for n in nodes:
                            try: neo4j_client.create_node(GraphNode(**n))
                            except: pass
                        for e in edges:
                            try: neo4j_client.create_edge(GraphEdge(**e))
                            except: pass
                        
                        with conversation_area:
                            st.caption(f"📊 สกัดได้ {len(nodes)} nodes, {len(edges)} edges")
                
                # Save to SQLite history
                save_debate(
                    topic=topic,
                    messages=messages,
                    rounds=auto_rounds,
                    node_count=node_count,
                    edge_count=edge_count
                )
                
                save_completed(topic)
                with log_area:
                    st.success(f"✅ **{topic}** - บันทึก {node_count} nodes")
                
                # Delay before next
                if i < len(pending) - 1:
                    with conversation_area:
                        st.markdown("---")
                    for sec in range(delay_between, 0, -1):
                        status_text.markdown(f"⏸️ **รอ {sec} วินาที** ก่อนหัวข้อถัดไป...")
                        time.sleep(1)
                        if not st.session_state.auto_running:
                            break
                
            except Exception as e:
                with log_area:
                    st.error(f"❌ {topic}: {e}")
                time.sleep(30)
        
        st.session_state.auto_running = False
        st.session_state.auto_current = None
        progress.progress(1.0)
        status_text.markdown("🎉 **Debate ทั้งหมดเสร็จสิ้น!**")
        st.balloons()
    
    st.subheader("📋 คิวหัวข้อ")
    for topic in topics:
        if topic in completed:
            st.markdown(f"<div class='topic-card topic-done'>✅ {topic}</div>", unsafe_allow_html=True)
        elif topic == st.session_state.auto_current:
            st.markdown(f"<div class='topic-card topic-current'>🔄 {topic}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='topic-card topic-pending'>⏳ {topic}</div>", unsafe_allow_html=True)

# ============================================
# TAB 3: Chat History
# ============================================
with tab3:
    st.header("📖 ประวัติการ Debate")
    
    # Stats
    try:
        stats = get_history_stats()
        col1, col2 = st.columns(2)
        col1.metric("📚 Debate ทั้งหมด", stats['debates'])
        col2.metric("💬 ข้อความทั้งหมด", stats['messages'])
    except:
        pass
    
    # Search
    search_query = st.text_input("🔍 ค้นหาหัวข้อ", key="history_search")
    
    # Load debates
    if search_query:
        debates = search_debates(search_query)
    else:
        debates = get_all_debates()
    
    if not debates:
        st.info("ยังไม่มีประวัติ - ลองรัน Debate ก่อน!")
    else:
        # Select debate
        st.subheader(f"📋 พบ {len(debates)} รายการ")
        
        for debate in debates:
            with st.expander(f"🎭 {debate['topic']} ({debate['created_at'][:10]})", expanded=False):
                st.caption(f"Rounds: {debate['rounds']} | Nodes: {debate['node_count']} | Edges: {debate['edge_count']}")
                
                # Load full debate
                full_debate = get_debate(debate['id'])
                
                if full_debate and full_debate['messages']:
                    # "Play All" button for entire debate
                    col_play, col_del = st.columns([0.8, 0.2])
                    with col_play:
                        if st.button("▶️ ฟังทั้งหัวข้อ", key=f"play_all_{debate['id']}", use_container_width=True):
                            st.info("🎙️ กำลังสร้างเสียง... กรุณารอสักครู่")
                            
                            # Pre-generate all audio files
                            import base64
                            audio_data_list = []
                            for msg in full_debate['messages']:
                                agent = msg['agent']
                                content = msg['content']
                                audio_bytes, _ = tts.get_audio_for_agent_with_duration(content, agent)
                                if audio_bytes:
                                    b64 = base64.b64encode(audio_bytes).decode()
                                    audio_data_list.append(b64)
                            
                            # Create JavaScript audio queue player
                            audio_js = f"""
                            <div id="audio-player-container">
                                <p id="audio-status">🎙️ กำลังเล่น 1/{len(audio_data_list)}</p>
                                <audio id="audio-player" controls autoplay style="width: 100%;"></audio>
                            </div>
                            <script>
                                const audioDataList = {audio_data_list};
                                let currentIndex = 0;
                                const audioPlayer = document.getElementById('audio-player');
                                const statusText = document.getElementById('audio-status');
                                
                                function playNext() {{
                                    if (currentIndex < audioDataList.length) {{
                                        statusText.textContent = '🎙️ กำลังเล่น ' + (currentIndex + 1) + '/' + audioDataList.length;
                                        audioPlayer.src = 'data:audio/mp3;base64,' + audioDataList[currentIndex];
                                        audioPlayer.play();
                                        currentIndex++;
                                    }} else {{
                                        statusText.textContent = '✅ เล่นเสร็จแล้ว!';
                                    }}
                                }}
                                
                                audioPlayer.onended = function() {{
                                    playNext();
                                }};
                                
                                // Start playing
                                playNext();
                            </script>
                            """
                            st.components.v1.html(audio_js, height=100)
                    with col_del:
                        if st.button("🗑️ ลบ", key=f"del_{debate['id']}", use_container_width=True):
                            delete_debate(debate['id'])
                            st.rerun()
                    
                    st.divider()
                    
                    for msg_idx, msg in enumerate(full_debate['messages']):
                        agent = msg['agent']
                        content = msg['content']
                        
                        render_message_with_tts(agent, content, f"hist_view_{debate['id']}_{msg_idx}")
                else:
                    st.warning("ไม่มีข้อความบันทึก")
                    
                    # Delete button
                    if st.button(f"🗑️ ลบ", key=f"del_{debate['id']}"):
                        delete_debate(debate['id'])
                        st.rerun()

# ============================================
# TAB 4: Graph
# ============================================
with tab4:
    st.header("📊 กราฟความรู้")
    
    if st.button("🔄 รีเฟรช", key="refresh_graph"):
        st.rerun()
    
    try:
        data = neo4j_client.get_all_graph_data()
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
        stats = neo4j_client.get_stats()
        
        col_n, col_e = st.columns(2)
        col_n.metric("🔵 Nodes", stats['nodes'])
        col_e.metric("🔗 Edges", stats['edges'])
        
        if nodes:
            type_color = {
                "concept": "#5e35b1", "technique": "#e53935",
                "risk": "#fb8c00", "defense": "#43a047", "book": "#1e88e5"
            }
            
            visual_nodes = [
                Node(
                    id=str(n['id']).replace(" ", "_"),
                    label=n.get('name', n['id'])[:30],
                    size=12,
                    color=type_color.get(n.get('type', 'concept'), "#5e35b1")
                )
                for n in nodes[:200]
            ]
            
            visual_edges = [
                Edge(
                    source=str(e['source']).replace(" ", "_"),
                    target=str(e['target']).replace(" ", "_"),
                    color="#8b949e"
                )
                for e in edges[:500]
            ]
            
            config = Config(width=800, height=600, directed=True, physics=True, hierarchical=False)
            agraph(nodes=visual_nodes, edges=visual_edges, config=config)
            
            # Node search
            st.subheader("📋 รายการ Nodes")
            search_node = st.text_input("🔍 ค้นหา", key="node_search")
            
            filtered = [n for n in nodes if search_node.lower() in n.get('name', '').lower()] if search_node else nodes
            
            for n in filtered[:30]:
                with st.expander(f"🔹 {n.get('name', n['id'])}"):
                    st.write(f"**ประเภท:** {n.get('type', 'N/A')}")
                    if n.get('description'):
                        st.write(n['description'])
        else:
            st.info("ยังไม่มีข้อมูลกราฟ - ลองรัน Debate ก่อน!")
            
    except Exception as e:
        st.error(f"Error: {e}")
