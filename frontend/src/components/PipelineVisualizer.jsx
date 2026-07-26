import React from 'react';
import './PipelineVisualizer.css';

const nodes = [
  { id: 'sourcing', icon: '📄', label: 'Sourcing' },
  { id: 'screening', icon: '🔍', label: 'Screening' },
  { id: 'scheduling', icon: '📅', label: 'Scheduling' },
  { id: 'interviewer', icon: '🎤', label: 'Interviewer' },
  { id: 'reporting', icon: '📊', label: 'Reporting' },
];

export default function PipelineVisualizer({ activeNode, completedNodes = [] }) {
  return (
    <div className="card">
      <div className="ch">
        <h2><span style={{fontSize: '18px'}}>🌐</span> LangGraph Agent Topology</h2>
      </div>
      <div className="cb">
        <div className="pipe">
          <div className="pnode mgr">
            <div className="picon">🧠</div>
            <div className="pname">Manager</div>
          </div>
          
          {nodes.map((node) => {
            const isActive = activeNode === node.id;
            const isDone = completedNodes.includes(node.id);
            let stateClass = '';
            if (isActive) stateClass = 'active';
            else if (isDone) stateClass = 'done';

            return (
              <React.Fragment key={node.id}>
                <div className={`parrow ${isDone || isActive ? 'on' : ''}`}></div>
                <div className={`pnode ${stateClass}`}>
                  <div className="picon">
                    {isDone ? (
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{color: 'var(--green)'}}>
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                    ) : (
                      node.icon
                    )}
                  </div>
                  <div className="pname">{node.label}</div>
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
