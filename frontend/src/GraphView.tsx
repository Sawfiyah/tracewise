import { useEffect, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

type GraphData = {
  project_id: string;
  nodes: {
    id: string;
    label: string;
    type: string;
  }[];
  edges: {
    source: string;
    target: string;
    type: string;
  }[];
  node_count: number;
  edge_count: number;
};

type GraphViewProps = {
  projectId: string;
};

export default function GraphView({ projectId }: GraphViewProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function fetchGraph() {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(
          `http://localhost:8000/projects/${projectId}/graph`
        );

        if (!response.ok) {
          throw new Error("Could not load the project graph.");
        }

        const data: GraphData = await response.json();

        if (cancelled) return;

        const graphNodes: Node[] = data.nodes.map((node, index) => ({
          id: node.id,
          position: {
            x: (index % 3) * 240,
            y: Math.floor(index / 3) * 140,
          },
          data: {
            label: node.label,
          },
          style: {
            background: "#ffffff",
            color: "#183c32",
            border: "1px solid #b8d5c9",
            borderRadius: "10px",
            padding: "14px 20px",
            fontWeight: 600,
            fontSize: 13,
            minWidth: 150,
            textAlign: "center",
          },
        }));

        const graphEdges: Edge[] = data.edges.map((edge, index) => ({
          id: `${edge.source}-${edge.target}-${index}`,
          source: edge.source,
          target: edge.target,
          label: edge.type,
          animated: true,
          style: {
            stroke: "#398568",
            strokeWidth: 2,
          },
        }));

        setNodes(graphNodes);
        setEdges(graphEdges);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Something went wrong loading the graph."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchGraph();

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (loading) {
    return <p>Loading function graph...</p>;
  }

  if (error) {
    return <p role="alert">{error}</p>;
  }

  if (nodes.length === 0) {
    return <p>No functions were found in this project.</p>;
  }

  return (
    <div
      style={{
        width: "100%",
        height: 420,
        border: "1px solid #dce7e1",
        borderRadius: 12,
        overflow: "hidden",
        background: "#f8fbf9",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
      >
        <Background color="#dce7e1" gap={20} />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}