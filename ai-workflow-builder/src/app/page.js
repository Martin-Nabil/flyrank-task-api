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
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);

  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onConnect = useCallback((connection) => {
    const isYes = window.confirm("Is this the YES path? (Cancel = NO path)");
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

  const runWorkflow = async () => {
    if (nodes.length === 0) return;

    setRunning(true);
    setRunResult(null);

    const edgesWithBranch = edges.map((e) => ({
      source: e.source,
      target: e.target,
      data: e.data,
    }));

    const response = await fetch("/api/run-workflow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nodes: nodes.map((n) => ({ id: n.id, data: n.data })),
        edges: edgesWithBranch,
        startNodeId: nodes[0].id,
      }),
    });

    const data = await response.json();
    setRunResult(data);
    setRunning(false);
  };
const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex" }}>
      <div style={{ flex: 1, position: "relative" }}>
        <div style={{ position: "absolute", top: 10, left: 10, zIndex: 10, display: "flex", gap: 8 }}>
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
          <button
            onClick={runWorkflow}
            disabled={running}
            style={{
              padding: "8px 16px",
              background: running ? "#9ca3af" : "#16a34a",
              color: "white",
              border: "none",
              borderRadius: 6,
              cursor: running ? "not-allowed" : "pointer",
            }}
          >
            {running ? "Running..." : "Run Workflow"}
          </button>
        </div>

        {runResult && (
          <div
            style={{
              position: "absolute",
              bottom: 10,
              left: 10,
              zIndex: 10,
              background: "white",
              border: "1px solid #e5e7eb",
              borderRadius: 6,
              padding: 12,
              maxWidth: 400,
              fontSize: 13,
            }}
          >
            <strong>Event sent!</strong> Check the Inngest dashboard's Runs tab
            (localhost:8288) for the execution log - event ID: {runResult.eventId}
          </div>
        )}

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