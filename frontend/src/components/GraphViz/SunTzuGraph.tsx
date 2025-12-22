'use client';

import dynamic from 'next/dynamic';
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import * as THREE from 'three';

// Type definitions
interface GraphNode {
  id: string;
  name: string;
  type: string;
  description?: string;
  val?: number;
  x?: number;
  y?: number;
  z?: number;
  color?: string;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  type?: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface NodeDetails {
  node: GraphNode;
  neighbors: { id: string; name: string; relation: string }[];
}

// Loading screen component
const LoadingScreen = () => (
  <div className="w-full h-[700px] flex items-center justify-center bg-black">
    <div className="text-center">
      <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
      <p className="text-purple-400 text-lg">กำลังโหลดจักรวาลความรู้...</p>
    </div>
  </div>
);

// Load 3D graph library client-side only
const ForceGraph3D = dynamic(
  () => import('react-force-graph-3d').then(mod => mod.default),
  { ssr: false, loading: () => <LoadingScreen /> }
) as any;

// API URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Neon Blue Space/Brain Color Palette
const nodeColors: Record<string, string> = {
  concept: '#00f0ff',    // Cyan neon
  technique: '#00d4ff',  // Electric blue
  risk: '#ff3366',       // Neon pink/red
  defense: '#00ff88',    // Neon green
  book: '#7c3aed',       // Deep purple
  chapter: '#6366f1',    // Indigo
  outcome: '#22d3ee',    // Light cyan
  person: '#f0abfc',     // Light pink
};

// Node type icons/symbols
const nodeSymbols: Record<string, string> = {
  concept: '◆',
  technique: '⚡',
  risk: '◈',
  defense: '◇',
  book: '▣',
  chapter: '▢',
  outcome: '◎',
  person: '●',
};

const CosmicGraph = () => {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeDetails | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [stats, setStats] = useState<{ nodes: number; edges: number } | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set<string>());
  const fgRef = useRef<any>(null);

  // Create sprite texture for node labels
  const createNodeSprite = useCallback((node: GraphNode) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d')!;

    const size = 128;
    canvas.width = size;
    canvas.height = size;

    // Get node color
    const color = nodeColors[node.type] || '#6b7280';
    const symbol = nodeSymbols[node.type] || '●';

    // Draw glowing circle (neuron body)
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gradient.addColorStop(0, color);
    gradient.addColorStop(0.5, color + '80');
    gradient.addColorStop(1, 'transparent');

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2 - 4, 0, Math.PI * 2);
    ctx.fill();

    // Draw inner circle
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 4, 0, Math.PI * 2);
    ctx.fill();

    // Draw symbol/emoji
    ctx.font = '24px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(symbol, size / 2, size / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthWrite: false
    });

    const sprite = new THREE.Sprite(material);
    sprite.scale.set(12, 12, 1);

    return sprite;
  }, []);

  // Create text label sprite
  const createLabelSprite = useCallback((text: string, color: string) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d')!;

    const fontSize = 14;
    ctx.font = `${fontSize}px Arial, sans-serif`;
    const textWidth = ctx.measureText(text.substring(0, 20)).width;

    canvas.width = Math.min(textWidth + 20, 200);
    canvas.height = fontSize + 10;

    // Semi-transparent background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.roundRect(0, 0, canvas.width, canvas.height, 4);
    ctx.fill();

    // Text
    ctx.font = `${fontSize}px Arial, sans-serif`;
    ctx.fillStyle = color;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text.substring(0, 18) + (text.length > 18 ? '...' : ''), canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthWrite: false
    });

    const sprite = new THREE.Sprite(material);
    sprite.scale.set(canvas.width / 8, canvas.height / 8, 1);
    sprite.position.y = -10;

    return sprite;
  }, []);

  // Custom node object with THREE.js
  const nodeThreeObject = useCallback((node: GraphNode) => {
    const group = new THREE.Group();

    const color = nodeColors[node.type] || '#6b7280';
    const nodeSize = node.type === 'book' ? 8 :
      node.type === 'chapter' ? 6 :
        node.type === 'technique' ? 5 : 4;

    // Neuron body (glowing sphere)
    const geometry = new THREE.SphereGeometry(nodeSize, 16, 16);
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color),
      transparent: true,
      opacity: 0.9
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // Outer glow
    const glowGeometry = new THREE.SphereGeometry(nodeSize * 1.5, 16, 16);
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color),
      transparent: true,
      opacity: 0.2
    });
    const glow = new THREE.Mesh(glowGeometry, glowMaterial);
    group.add(glow);

    // Add text label
    const label = createLabelSprite(node.name, color);
    label.position.y = -nodeSize - 5;
    group.add(label);

    return group;
  }, [createLabelSprite]);

  // Fetch graph data from API
  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/graph`);

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();

      // Transform nodes
      const nodes = data.nodes.map((n: any) => ({
        id: n.id,
        name: n.name || n.id,
        type: n.type || 'concept',
        description: n.description,
        color: nodeColors[n.type] || '#6b7280',
        val: n.type === 'book' ? 30 : n.type === 'chapter' ? 20 : 10
      }));

      const links = data.edges.map((e: any) => ({
        source: e.source,
        target: e.target,
        type: e.type
      }));

      setGraphData({ nodes, links });
      setStats(data.stats);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch graph:', err);
      // Suppress error in auto-refresh mode to avoid spam
      // setError('ไม่สามารถโหลดข้อมูลกราฟได้');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch node details
  const fetchNodeDetails = async (nodeId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/node/${encodeURIComponent(nodeId)}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedNode(data);
      }
    } catch (err) {
      console.error('Failed to fetch node details:', err);
    }
  };

  // Search handler
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setHighlightNodes(new Set<string>());
      return;
    }
    try {
      const response = await fetch(`${API_URL}/api/search?q=${encodeURIComponent(searchQuery)}&limit=50`);
      if (response.ok) {
        const data = await response.json();
        const nodeIds = new Set<string>(data.results.map((r: any) => r.id));
        setHighlightNodes(nodeIds);

        if (data.results.length > 0 && fgRef.current) {
          const node = graphData.nodes.find(n => n.id === data.results[0].id);
          if (node && node.x !== undefined) {
            fgRef.current.cameraPosition(
              { x: node.x, y: node.y, z: (node.z || 0) + 200 },
              node, 2000
            );
          }
        }
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  // Node click handler
  const handleNodeClick = (node: GraphNode) => {
    fetchNodeDetails(node.id);
    if (fgRef.current && node.x !== undefined) {
      fgRef.current.cameraPosition(
        { x: node.x, y: node.y, z: (node.z || 0) + 100 },
        node, 1000
      );
    }
  };

  useEffect(() => {
    setIsMounted(true);
    fetchGraph();

    // Auto-refresh every 5 seconds (Monitor Mode)
    const interval = setInterval(() => {
      fetchGraph();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchGraph]);

  if (!isMounted) return null;

  return (
    <div className="w-full min-h-screen bg-black overflow-hidden">
      {/* Header */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-black/90 backdrop-blur-md border-b border-cyan-900/50 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 bg-clip-text text-transparent mb-3">
            🧠 กราฟเชื่อมโยงข้อมูล
          </h1>

          <div className="flex flex-wrap gap-4 items-center justify-between">
            <div className="flex gap-6 text-sm">
              <span className="text-cyan-400">
                ◆ <span className="text-white font-bold">{stats?.nodes || graphData.nodes.length}</span> โหนด
              </span>
              <span className="text-blue-400">
                ⚡ <span className="text-white font-bold">{stats?.edges || graphData.links.length}</span> การเชื่อมต่อ
              </span>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="ค้นหา..."
                className="px-4 py-2 rounded-full bg-cyan-900/30 border border-cyan-700/50 text-white text-sm focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 w-48"
              />
              <button onClick={handleSearch}
                className="px-5 py-2 rounded-full bg-gradient-to-r from-cyan-600 to-blue-600 text-white text-sm font-medium hover:from-cyan-500 hover:to-blue-500 shadow-lg shadow-cyan-500/20">
                🔍
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="fixed top-32 left-1/2 transform -translate-x-1/2 z-50 p-4 bg-red-900/80 backdrop-blur border border-red-700 rounded-lg text-red-200 text-sm">
          {error}
        </div>
      )}

      {/* 3D Graph */}
      <div className="pt-32">
        {loading && !graphData.nodes.length ? (
          <LoadingScreen />
        ) : (
          <ForceGraph3D
            ref={fgRef}
            graphData={graphData}
            nodeThreeObject={nodeThreeObject}
            nodeThreeObjectExtend={false}
            linkColor={() => 'rgba(0, 200, 255, 0.25)'}
            linkWidth={0.8}
            linkOpacity={0.5}
            // Neural network style: curved links with particles
            linkCurvature={0.15}
            linkDirectionalParticles={3}
            linkDirectionalParticleWidth={2}
            linkDirectionalParticleSpeed={0.004}
            linkDirectionalParticleColor={() => '#00f0ff'}
            backgroundColor="#000000"
            onNodeClick={handleNodeClick}
            enableNodeDrag={true}
            // Physics for brain-like spread
            d3AlphaDecay={0.008}
            d3VelocityDecay={0.25}
            warmupTicks={150}
            cooldownTicks={300}
            d3Force={(d3: any) => {
              d3.force('charge').strength(-200);
              d3.force('center').strength(0.03);
              d3.force('link').distance(100);
            }}
          />
        )}
      </div>

      {/* Node details panel */}
      {selectedNode && (
        <div className="fixed top-28 right-6 w-80 p-5 bg-black/95 backdrop-blur-xl border border-cyan-800/50 rounded-2xl shadow-2xl z-50">
          <button onClick={() => setSelectedNode(null)}
            className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full bg-cyan-900/50 text-gray-400 hover:text-white">
            ✕
          </button>

          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">{nodeSymbols[selectedNode.node.type] || '●'}</span>
            <h3 className="font-bold text-lg text-white">{selectedNode.node.name}</h3>
          </div>

          <span className="inline-block px-3 py-1 rounded-full text-xs font-medium mb-3"
            style={{ backgroundColor: nodeColors[selectedNode.node.type] + '30', color: nodeColors[selectedNode.node.type] }}>
            {selectedNode.node.type}
          </span>

          {selectedNode.node.description && (
            <p className="text-gray-300 text-sm mb-4">{selectedNode.node.description}</p>
          )}

          {selectedNode.neighbors?.length > 0 && (
            <div>
              <h4 className="text-cyan-400 text-xs uppercase mb-2">⚡ เชื่อมต่อกับ ({selectedNode.neighbors.length})</h4>
              <ul className="space-y-1.5 max-h-48 overflow-y-auto">
                {selectedNode.neighbors.slice(0, 10).map((n, i) => (
                  <li key={i} className="text-sm text-gray-300 flex items-center gap-2">
                    <span className="text-purple-500 text-xs">{n.relation || '→'}</span>
                    <span className="truncate">{n.name}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 text-center">
        <p className="text-gray-600 text-xs bg-black/80 backdrop-blur px-4 py-2 rounded-full border border-cyan-900/30">
          ลาก = หมุน | Scroll = ซูม | คลิก = ดูรายละเอียด
        </p>
      </div>
    </div>
  );
};

export default CosmicGraph;