import { useEffect, useState } from 'react';

export default function CausalReconstruction({ causal_graph, selectedScenario }) {
  const [visibleNodes, setVisibleNodes] = useState([]);

  // Progressive reveal animation
  useEffect(() => {
    if (!causal_graph || !causal_graph.critical_path) return;
    setVisibleNodes([]);
    
    causal_graph.critical_path.forEach((nodeId, idx) => {
      setTimeout(() => {
        setVisibleNodes(prev => [...prev, nodeId]);
      }, idx * 180); // 180ms delay per node
    });
  }, [causal_graph]);

  return (
    <div className="panel causal-panel">
      <div className="panel-header">
        <h2>WHAT CAUSED THE STOP?</h2>
        <div className="panel-subtitle">Strongest explanation supported by the production data</div>
      </div>
      <div className="dag-container">
        {causal_graph.critical_path.map((nodeId, idx) => {
          const node = causal_graph.nodes.find(n => n.id === nodeId);
          if (!node) return null;
          
          let isHighlighted = false;
          if (selectedScenario === 'intervention-a' && nodeId === 'IR_STROBE') isHighlighted = true;
          if (selectedScenario === 'intervention-b' && nodeId === 'PACKET_LOSS') isHighlighted = true;

          const isVisible = visibleNodes.includes(nodeId);

          let primary = node.description;
          let secondary = null;
          
          if (node.description === "IR Strobe Interference") {
            primary = "INFRARED LIGHT INTERFERENCE";
            secondary = "Tracking system affected";
          } else if (node.description === "Optical Tracking Packet Loss") {
            primary = "CAMERA TRACKING SIGNAL DROPPED";
          } else if (node.description === "UE5 Frustum Tracking Jitter") {
            primary = "CAMERA POSITION BECAME UNSTABLE";
            secondary = "Unreal Engine detected tracking jitter";
          } else if (node.description === "Camera Recording Halt") {
            primary = "CAMERA STOPPED RECORDING";
          } else if (node.description === "DIT Ingest Buffer Saturation") {
            primary = "FOOTAGE BACKUP NEARLY FULL";
          } else if (node.description === "Stage 4 Production Halt") {
            primary = "FILMING STOPPED";
          } else if (node.description === "Schedule Delay") {
            primary = "SHOOT FALLS BEHIND SCHEDULE";
          } else if (node.description === "Cost / Contract Exposure") {
            primary = "COST AND CONTRACT RISK";
          }

          return (
            <div key={nodeId} className={`dag-node-wrapper ${isVisible ? 'visible' : 'hidden'}`}>
              <div className={`dag-node ${isHighlighted ? 'intervened' : ''}`}>
                <div>{primary}</div>
                {secondary && <div className="panel-subtitle" style={{marginTop: '4px', color: 'inherit', opacity: 0.8}}>{secondary}</div>}
              </div>
              {idx < causal_graph.critical_path.length - 1 && (
                <div className="dag-arrow">&darr;</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
