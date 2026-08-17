"use client";

import { useState, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
} from "reactflow";
import "reactflow/dist/style.css";

let nodeIdCounter = 2;

const initialNodes = [
  {
    id: "1",
    position: { x: 250, y: 50 },
    data: { label: "Is this a support request?" },
  },
];

const initialEdges = [];

export default function Home() {
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback((connection) => {
    // Ask which path this edge represents
    const isYes = window.confirm(
      "Is this the YES path? (Cancel = NO path)"
    );
    const label = isYes ? "YES" : "NO";
    const color = isYes ? "#16a34a" : "#dc2626";

    setEdges((eds) =>
      addEdge(
        {
          ...connection,
          label,
          style: { stroke: color },
          labelStyle: { fill: color, fontWeight: 700 },
          data: { branch: label },
        },
        eds
      )
    );
  }, []);

  const addNode = () => {
    const id = String(nodeIdCounter++);
    const newNode = {
      id,
      position: { x: 250, y: 100 + nodeIdCounter * 80 },
      data: { label: "New decision node" },
    };
    setNodes((nds) => [...nds, newNode]);
  };

  const onNodeClick = useCallback((event, node) => {
    setSelectedNodeId(node.id);
  }, []);

  const updateSelectedNodeLabel = (newLabel) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === selectedNodeId ? { ...n, data: { ...n.data, label: newLabel } } : n
      )
    );
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex" }}>
      <div style={{ flex: 1, position: "relative" }}>
        <div style={{ position: "absolute", top: 10, left: 10, zIndex: 10 }}>
          <button
            onClick={addNode}
            style={{
              padding: "8px 16px",
              background: "#2563eb",
              color: "white",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            + Add Decision Node
          </button>
        </div>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>

      {selectedNode && (
        <div
          style={{
            width: 300,
            padding: 16,
            borderLeft: "1px solid #e5e7eb",
            background: "#fafafa",
          }}
        >
          <h3 style={{ marginBottom: 8, fontWeight: 600 }}>Edit Node</h3>
          <label style={{ fontSize: 13, color: "#555" }}>Prompt (question the AI will answer YES/NO to):</label>
          <textarea
            value={selectedNode.data.label}
            onChange={(e) => updateSelectedNodeLabel(e.target.value)}
            rows={4}
            style={{ width: "100%", marginTop: 8, padding: 8 }}
          />
        </div>
      )}
    </div>
  );
}