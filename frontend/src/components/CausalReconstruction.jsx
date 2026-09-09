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
        <h2>CAUSAL RECONSTRUCTION</h2>
        <div className="panel-subtitle">STRONGEST SUPPORTED CAUSAL EXPLANATION</div>
      </div>
      <div className="dag-container">
        {causal_graph.critical_path.map((nodeId, idx) => {
          const node = causal_graph.nodes.find(n => n.id === nodeId);
          if (!node) return null;
          
          let isHighlighted = false;
          if (selectedScenario === 'intervention-a' && nodeId === 'IR_STROBE') isHighlighted = true;
          if (selectedScenario === 'intervention-b' && nodeId === 'PACKET_LOSS') isHighlighted = true;

          const isVisible = visibleNodes.includes(nodeId);

          return (
            <div key={nodeId} className={`dag-node-wrapper ${isVisible ? 'visible' : 'hidden'}`}>
              <div className={`dag-node ${isHighlighted ? 'intervened' : ''}`}>
                {node.description}
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
