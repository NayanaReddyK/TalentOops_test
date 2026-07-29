import React from 'react';
import {
  Brain,
  FileSearch,
  Filter,
  Calendar,
  Mic,
  FileBarChart,
  Check,
  Loader2,
} from 'lucide-react';

const steps = [
  { id: 'manager', icon: Brain, label: 'Manager', isOrchestrator: true },
  { id: 'sourcing', icon: FileSearch, label: 'Sourcing' },
  { id: 'screening', icon: Filter, label: 'Screening' },
  { id: 'scheduling', icon: Calendar, label: 'Scheduling' },
  { id: 'interviewer', icon: Mic, label: 'Interviewer' },
  { id: 'reporting', icon: FileBarChart, label: 'Reporting' },
];

export default function PipelineVisualizer({ activeNode, completedNodes = [] }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-5">
      {/* Header */}
      <h2 className="mb-5 text-sm font-semibold tracking-wide text-white/70 uppercase">
        Pipeline Progress
      </h2>

      {/* Vertical stepper */}
      <div className="flex flex-col">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1;
          const hasStarted = activeNode !== '' || completedNodes.length > 0;
          const isFinished = activeNode === '' && completedNodes.length > 0;

          const isActive = step.isOrchestrator ? (hasStarted && !isFinished) : activeNode === step.id;
          const isDone = step.isOrchestrator ? isFinished : completedNodes.includes(step.id);

          const StepIcon = step.icon;

          return (
            <div key={step.id} className="flex gap-3">
              {/* Left column: indicator + connector line */}
              <div className="flex flex-col items-center">
                {/* Status circle */}
                <div
                  className={`
                    relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                    transition-colors duration-300
                    ${isDone
                      ? 'bg-emerald-400/15 text-emerald-400'
                      : isActive
                        ? 'bg-cyan-400/15 text-cyan-400'
                        : 'bg-white/[0.06] text-white/30'
                    }
                  `}
                >
                  {isDone ? (
                    <Check size={15} strokeWidth={2.5} />
                  ) : isActive ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <StepIcon size={15} />
                  )}

                  {/* Active pulse ring */}
                  {isActive && (
                    <span className="absolute inset-0 animate-ping rounded-full bg-cyan-400/20" />
                  )}
                </div>

                {/* Connector line */}
                {!isLast && (
                  <div
                    className={`
                      w-px flex-1 min-h-5 transition-colors duration-300
                      ${isDone ? 'bg-emerald-400/30' : 'bg-white/[0.08]'}
                    `}
                  />
                )}
              </div>

              {/* Right column: label + meta */}
              <div className={`pb-5 ${isLast ? 'pb-0' : ''}`}>
                <div className="flex items-center gap-2">
                  <span
                    className={`
                      text-sm font-medium leading-8 transition-colors duration-300
                      ${isDone
                        ? 'text-white/80'
                        : isActive
                          ? 'text-cyan-400'
                          : 'text-white/40'
                      }
                    `}
                  >
                    {step.label}
                  </span>

                  {step.isOrchestrator && (
                    <span className="rounded-full bg-purple-400/10 px-2 py-0.5 text-[10px] font-semibold tracking-wider text-purple-400 uppercase">
                      Orchestrator
                    </span>
                  )}
                </div>

                {/* Status text */}
                <p className="text-xs text-white/25">
                  {isDone
                    ? 'Completed'
                    : isActive
                      ? 'In progress…'
                      : 'Pending'}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
