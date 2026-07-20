import { useCallback, useEffect, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Boxes, Braces, Database, FileCode2, Layers3, Server, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useRepositorySourceFile } from "@/features/repositories/repository-queries";

const kindStyle = {
  repository: { icon: Boxes, tone: "border-primary bg-primary/10 text-primary" },
  frontend: { icon: Braces, tone: "border-cyan-500/40 bg-cyan-500/10 text-cyan-700" },
  backend: { icon: Server, tone: "border-violet-500/40 bg-violet-500/10 text-violet-700" },
  source: { icon: Layers3, tone: "border-border bg-muted/60 text-foreground" },
  service: { icon: Server, tone: "border-amber-500/40 bg-amber-500/10 text-amber-700" },
  database: { icon: Database, tone: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700" },
  infrastructure: { icon: Boxes, tone: "border-rose-500/40 bg-rose-500/10 text-rose-700" },
};

function ArchitectureNode({ data }) {
  const style = kindStyle[data.kind] ?? kindStyle.source;
  const Icon = style.icon;
  return (
    <div className={`min-w-44 rounded-xl border p-3 shadow-sm ${style.tone}`}>
      <Handle type="target" position={Position.Left} className="!size-2 !border-0 !bg-border" />
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{data.label}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-4 text-muted-foreground">{data.description}</p>
          {data.file_path ? <p className="mt-2 truncate text-[11px] font-medium">Open {data.file_path}</p> : null}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!size-2 !border-0 !bg-border" />
    </div>
  );
}

const nodeTypes = { architecture: ArchitectureNode };
const legendKinds = ["frontend", "backend", "service", "database", "infrastructure"];

export function ArchitectureGraphPanel({ repositoryId, graph, error, isLoading }) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!graph) {
      setNodes([]);
      setEdges([]);
      return;
    }
    setNodes(layoutNodes(graph.nodes));
    setEdges(
      graph.edges.map((edge) => ({
        ...edge,
        type: "smoothstep",
        animated: Boolean(edge.label),
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        label: edge.label,
      })),
    );
  }, [graph, setEdges, setNodes]);

  const onNodeClick = useCallback((_event, node) => {
    setSelectedNode(node.data.file_path ? node.data : null);
  }, []);

  if (isLoading) {
    return <div className="mt-8 h-112 animate-pulse rounded-xl border border-border bg-muted/40" />;
  }
  if (!graph) {
    const message = error?.status === 404
      ? "Analyze this repository to generate its architecture graph."
      : error?.message ?? "The architecture graph is unavailable.";
    return (
      <Card className="mt-8 border-dashed">
        <CardHeader>
          <p className="text-sm font-medium text-primary">Architecture graph</p>
          <CardTitle className="mt-1">Map your system</CardTitle>
          <CardDescription className="mt-1">{message}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="mt-8 overflow-hidden">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-primary">Architecture graph</p>
            <CardTitle className="mt-1">Navigate your system</CardTitle>
            <CardDescription className="mt-1">Pan, zoom, and select source-backed nodes to open their files.</CardDescription>
          </div>
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">Analysis v{graph.analysis_version}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-[33rem] overflow-hidden rounded-xl border border-border bg-muted/20">
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              minZoom={0.25}
              maxZoom={1.75}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={18} size={1} />
              <Controls showInteractive={false} />
              <MiniMap pannable zoomable nodeColor={(node) => miniMapColor(node.data?.kind)} />
            </ReactFlow>
          </ReactFlowProvider>
        </div>
        <GraphLegend />
        <SourcePreview repositoryId={repositoryId} node={selectedNode} onClose={() => setSelectedNode(null)} />
      </CardContent>
    </Card>
  );
}

function layoutNodes(graphNodes) {
  const lanes = {
    repository: { x: 0, y: 230 },
    frontend: { x: 250, y: 40 },
    backend: { x: 250, y: 200 },
    source: { x: 250, y: 380 },
    service: { x: 520, y: 100 },
    database: { x: 790, y: 220 },
    infrastructure: { x: 520, y: 410 },
  };
  const offsets = {};
  return graphNodes.map((node) => {
    const lane = lanes[node.kind] ?? lanes.source;
    const index = offsets[node.kind] ?? 0;
    offsets[node.kind] = index + 1;
    return {
      id: node.id,
      type: "architecture",
      data: node,
      position: { x: lane.x, y: lane.y + index * 130 },
    };
  });
}

function GraphLegend() {
  return <div className="flex flex-wrap gap-2">{legendKinds.map((kind) => <span key={kind} className={`rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${kindStyle[kind].tone}`}>{kind}</span>)}</div>;
}

function SourcePreview({ repositoryId, node, onClose }) {
  const { data, error, isLoading } = useRepositorySourceFile(repositoryId, node?.file_path);
  if (!node) {
    return <p className="text-sm text-muted-foreground">Select a service, database, or infrastructure node to open its source file.</p>;
  }
  return (
    <div className="rounded-xl border border-border bg-muted/20">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0"><p className="flex items-center gap-2 text-sm font-semibold"><FileCode2 className="size-4 text-primary" aria-hidden="true" />{node.file_path}</p>{node.line ? <p className="mt-1 text-xs text-muted-foreground">Highlighted symbol starts at line {node.line}.</p> : null}</div>
        <Button variant="ghost" size="icon" type="button" onClick={onClose} aria-label="Close file preview"><X className="size-4" /></Button>
      </div>
      {isLoading ? <div className="h-40 animate-pulse" /> : null}
      {error ? <p className="p-4 text-sm text-red-700">{error.message}</p> : null}
      {data ? <pre className="max-h-96 overflow-auto p-4 text-xs leading-5 text-muted-foreground"><code>{data.content}</code></pre> : null}
    </div>
  );
}

function miniMapColor(kind) {
  const colors = { repository: "#3b82f6", frontend: "#06b6d4", backend: "#8b5cf6", service: "#f59e0b", database: "#10b981", infrastructure: "#f43f5e" };
  return colors[kind] ?? "#64748b";
}
