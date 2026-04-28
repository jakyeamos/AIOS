"use client";

import "@xyflow/react/dist/style.css";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  type Node,
  type NodeProps,
  type Edge,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
  Panel,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";

import type { WorkflowProposalDetail, WorkflowStage } from "@/server/routers/workflows";
import { trpc } from "@/lib/trpc";

// ─── Constants ───────────────────────────────────────────────────────────────

const KIND_COLORS: Record<string, string> = {
  parse_request: "#60a5fa",
  normalize_prompt: "#a78bfa",
  enrich_context: "#34d399",
  generate: "#4ade80",
  transform: "#fb923c",
  validate: "#fbbf24",
  finalize: "#6b7280",
};

const KIND_LABELS: Record<string, string> = {
  parse_request: "Parse",
  normalize_prompt: "Normalize",
  enrich_context: "Enrich",
  generate: "Generate",
  transform: "Transform",
  validate: "Validate",
  finalize: "Finalize",
};

const STAGE_KINDS = Object.keys(KIND_COLORS);
const NODE_WIDTH = 260;
const NODE_HEIGHT = 100;
const NODE_GAP = 60;

// ─── Stage node data type ─────────────────────────────────────────────────────

type StageNodeData = {
  stage: WorkflowStage;
  index: number;
  selected: boolean;
  onSelect: (index: number) => void;
};

// ─── Stage node component ─────────────────────────────────────────────────────

function StageNode({ data }: NodeProps) {
  const d = data as StageNodeData;
  const { stage, index, selected, onSelect } = d;
  const color = KIND_COLORS[stage.kind] ?? "#6b7280";
  const label = KIND_LABELS[stage.kind] ?? stage.kind;

  return (
    <div
      className={`wf-node${selected ? " wf-node-selected" : ""}`}
      style={{ "--node-accent": color } as React.CSSProperties}
      onClick={() => onSelect(index)}
    >
      <Handle type="target" position={Position.Top} className="wf-handle" />
      <div className="wf-node-header">
        <span className="wf-node-index">{index + 1}</span>
        <span className="wf-node-key">{stage.key || <span className="wf-node-placeholder">untitled step</span>}</span>
        <span className="wf-node-kind">{label}</span>
      </div>
      {stage.required_skills.length > 0 && (
        <div className="wf-node-skills">
          {stage.required_skills.map((skill) => (
            <span key={skill} className="wf-skill-chip">{skill}</span>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="wf-handle" />
    </div>
  );
}

const nodeTypes = { stageNode: StageNode };

// ─── Layout helpers ───────────────────────────────────────────────────────────

const stagesToNodes = (
  stages: WorkflowStage[],
  selectedIndex: number | null,
  onSelect: (i: number) => void,
): Node[] =>
  stages.map((stage, index) => ({
    id: `stage-${index}`,
    type: "stageNode",
    position: { x: 0, y: index * (NODE_HEIGHT + NODE_GAP) },
    data: { stage, index, selected: index === selectedIndex, onSelect } as StageNodeData,
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
  }));

const stagesToEdges = (stages: WorkflowStage[]): Edge[] =>
  stages.slice(0, -1).map((_, index) => ({
    id: `e-${index}-${index + 1}`,
    source: `stage-${index}`,
    target: `stage-${index + 1}`,
    type: "smoothstep",
    style: { stroke: "#2a2a32", strokeWidth: 2 },
    animated: false,
  }));

// ─── Config panel ─────────────────────────────────────────────────────────────

type ConfigPanelProps = {
  stage: WorkflowStage;
  index: number;
  total: number;
  skillKeys: string[];
  onChange: (patch: Partial<WorkflowStage>) => void;
  onMove: (index: number, dir: -1 | 1) => void;
  onRemove: (index: number) => void;
  onClose: () => void;
};

function ConfigPanel({ stage, index, total, skillKeys, onChange, onMove, onRemove, onClose }: ConfigPanelProps) {
  const color = KIND_COLORS[stage.kind] ?? "#6b7280";

  const toggleSkill = (skill: string) => {
    const has = stage.required_skills.includes(skill);
    onChange({
      required_skills: has
        ? stage.required_skills.filter((k) => k !== skill)
        : [...stage.required_skills, skill],
    });
  };

  const updateBp = (i: number, value: string) => {
    const bps = [...(stage.best_practices ?? [])];
    bps[i] = value;
    onChange({ best_practices: bps });
  };

  return (
    <div className="wf-config-panel">
      <div className="wf-config-header" style={{ borderColor: color }}>
        <div>
          <span className="wf-config-step">Step {index + 1}</span>
          <span className="wf-config-kind" style={{ color }}>{KIND_LABELS[stage.kind] ?? stage.kind}</span>
        </div>
        <div className="wf-config-actions">
          <button type="button" className="wf-icon-btn" disabled={index === 0} onClick={() => onMove(index, -1)} title="Move up">↑</button>
          <button type="button" className="wf-icon-btn" disabled={index === total - 1} onClick={() => onMove(index, 1)} title="Move down">↓</button>
          <button type="button" className="wf-icon-btn wf-icon-btn-danger" onClick={() => { onRemove(index); onClose(); }} title="Delete step">✕</button>
          <button type="button" className="wf-icon-btn" onClick={onClose} title="Close">—</button>
        </div>
      </div>

      <div className="wf-config-body">
        <label className="wf-field">
          Step key
          <input value={stage.key} placeholder="e.g. humanize_output" onChange={(e) => onChange({ key: e.target.value })} />
        </label>

        <label className="wf-field">
          Kind
          <select value={stage.kind} onChange={(e) => onChange({ kind: e.target.value })}>
            {STAGE_KINDS.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </label>

        <div className="wf-field">
          <span>Skills</span>
          <div className="wf-skill-grid">
            {skillKeys.map((skill) => (
              <button
                key={skill}
                type="button"
                className={`wf-skill-toggle${stage.required_skills.includes(skill) ? " active" : ""}`}
                onClick={() => toggleSkill(skill)}
              >
                {stage.required_skills.includes(skill) && <span className="wf-skill-check">✓</span>}
                {skill}
              </button>
            ))}
          </div>
        </div>

        <div className="wf-field">
          <div className="wf-field-row">
            <span>Best practices</span>
            <button
              type="button"
              className="wf-add-btn"
              onClick={() => onChange({ best_practices: [...(stage.best_practices ?? []), ""] })}
            >
              + Add
            </button>
          </div>
          <div className="wf-bp-list">
            {(stage.best_practices ?? []).map((bp, i) => (
              <div key={i} className="wf-bp-row">
                <input
                  value={bp}
                  placeholder="e.g. Run humanizer before submission"
                  onChange={(e) => updateBp(i, e.target.value)}
                />
                <button
                  type="button"
                  className="wf-icon-btn wf-icon-btn-danger"
                  onClick={() =>
                    onChange({ best_practices: (stage.best_practices ?? []).filter((_, j) => j !== i) })
                  }
                >✕</button>
              </div>
            ))}
          </div>
        </div>

        <label className="wf-field">
          Notes
          <textarea
            rows={3}
            value={stage.notes ?? ""}
            placeholder="Why this step exists, edge cases, how to extend it"
            onChange={(e) => onChange({ notes: e.target.value })}
          />
        </label>
      </div>
    </div>
  );
}

// ─── Main sandbox ─────────────────────────────────────────────────────────────

type Props = {
  proposal: WorkflowProposalDetail;
  skillKeys: string[];
};

export function WorkflowSandbox({ proposal, skillKeys }: Props) {
  const [stages, setStages] = useState<WorkflowStage[]>(proposal.stages);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [saved, setSaved] = useState(false);

  const handleSelect = useCallback((index: number) => {
    setSelectedIndex((prev) => (prev === index ? null : index));
  }, []);

  const nodes = useMemo(
    () => stagesToNodes(stages, selectedIndex, handleSelect),
    [stages, selectedIndex, handleSelect],
  );
  const initialEdges = useMemo(() => stagesToEdges(stages), [stages]);

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync stages → flow nodes when stages change
  useEffect(() => {
    setFlowNodes(stagesToNodes(stages, selectedIndex, handleSelect));
    setEdges(stagesToEdges(stages));
  }, [stages, selectedIndex, handleSelect, setFlowNodes, setEdges]);

  const onConnect: OnConnect = useCallback(
    (connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges],
  );

  const updateMutation = trpc.workflows.updateStages.useMutation({
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 2200);
    },
  });

  const updateStage = (index: number, patch: Partial<WorkflowStage>) => {
    setStages((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
    setSaved(false);
  };

  const addStage = () => {
    const newStage: WorkflowStage = {
      key: "",
      kind: "generate",
      required_skills: [],
      best_practices: [],
      notes: "",
    };
    setStages((prev) => [...prev, newStage]);
    setSelectedIndex(stages.length);
    setSaved(false);
  };

  const removeStage = (index: number) => {
    setStages((prev) => prev.filter((_, i) => i !== index));
    setSelectedIndex(null);
    setSaved(false);
  };

  const moveStage = (index: number, dir: -1 | 1) => {
    const next = index + dir;
    if (next < 0 || next >= stages.length) return;
    setStages((prev) => {
      const copy = [...prev];
      [copy[index], copy[next]] = [copy[next], copy[index]];
      return copy;
    });
    setSelectedIndex(next);
    setSaved(false);
  };

  const handleSave = () => {
    updateMutation.mutate({
      id: proposal.id,
      stages: stages.map((s) => ({
        key: s.key,
        kind: s.kind,
        required_skills: s.required_skills,
        best_practices: s.best_practices ?? [],
        notes: s.notes ?? "",
      })),
    });
  };

  const selectedStage = selectedIndex !== null ? stages[selectedIndex] : null;

  return (
    <div className="wf-sandbox">
      {/* Canvas */}
      <div className="wf-canvas">
        <ReactFlow
          nodes={flowNodes}
          edges={edges}
          onNodesChange={onNodesChange as OnNodesChange}
          onEdgesChange={onEdgesChange as OnEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.4}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#1e1e24" />
          <Controls className="wf-controls" showInteractive={false} />
          <MiniMap
            className="wf-minimap"
            nodeColor={(node) => {
              const d = node.data as StageNodeData;
              return KIND_COLORS[d.stage?.kind] ?? "#6b7280";
            }}
            maskColor="rgba(10,10,11,0.7)"
          />
          <Panel position="top-right" className="wf-toolbar">
            <span className="wf-status-tag">{proposal.status}</span>
            <button type="button" className="wf-btn-secondary" onClick={addStage}>
              + Add step
            </button>
            <button
              type="button"
              className={`wf-btn-primary${saved ? " wf-btn-saved" : ""}`}
              disabled={updateMutation.isPending}
              onClick={handleSave}
            >
              {updateMutation.isPending ? "Saving…" : saved ? "✓ Saved" : "Save"}
            </button>
          </Panel>
        </ReactFlow>
      </div>

      {/* Config panel */}
      <div className={`wf-config-wrap${selectedStage !== null ? " open" : ""}`}>
        {selectedStage !== null && selectedIndex !== null && (
          <ConfigPanel
            stage={selectedStage}
            index={selectedIndex}
            total={stages.length}
            skillKeys={skillKeys}
            onChange={(patch) => updateStage(selectedIndex, patch)}
            onMove={moveStage}
            onRemove={removeStage}
            onClose={() => setSelectedIndex(null)}
          />
        )}
      </div>
    </div>
  );
}
