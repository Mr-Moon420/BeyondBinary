import { useState, useEffect } from 'react';
import type { FC } from 'react';
import {
  CheckCircle2,
  RotateCw,
  Circle,
  Cpu,
  Clock,
  Sparkles
} from 'lucide-react';

interface AnalysisProgressStepperProps {
  isAnalyzing: boolean;
  onComplete?: () => void;
}

interface PipelineStage {
  step: number;
  title: string;
  detail: string;
  model: string;
  durationMs: number;
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    step: 1,
    title: 'Manuscript Ingestion & Segmentation',
    detail: 'Tokenizing input text and isolating discrete sentence candidates via NLP parser',
    model: 'spaCy en_core_web_sm',
    durationMs: 2500,
  },
  {
    step: 2,
    title: 'Check-Worthy Claim Extraction',
    detail: 'Filtering factual check-worthy statements (CFS) from editorial rhetoric and filler',
    model: 'ClaimBuster DeBERTa-v2',
    durationMs: 4500,
  },
  {
    step: 3,
    title: 'Hybrid Multi-Tier Evidence Retrieval',
    detail: 'Searching local FAISS vector corpus with live Wikipedia & Wire fallback',
    model: 'all-MiniLM-L6-v2 + FAISS',
    durationMs: 5000,
  },
  {
    step: 4,
    title: 'Natural Language Inference Verification',
    detail: 'Evaluating Premise-Hypothesis entailment, neutral, and contradiction probabilities',
    model: 'RoBERTa-large-MNLI',
    durationMs: 7000,
  },
  {
    step: 5,
    title: 'Ideological Stance & Framing Scrutiny',
    detail: 'Calculating political spectrum distribution, AllSides domain grounding & rhetoric density',
    model: 'Political Bias BERT + AllSides KB',
    durationMs: 4000,
  },
];

export const AnalysisProgressStepper: FC<AnalysisProgressStepperProps> = ({
  isAnalyzing,
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Timer counter while analyzing
  useEffect(() => {
    if (!isAnalyzing) {
      setCurrentStep(1);
      setElapsedSeconds(0);
      return;
    }

    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [isAnalyzing]);

  // Stage advancement simulation synchronized with backend model times
  useEffect(() => {
    if (!isAnalyzing) return;

    let accumulatedTime = 0;
    const timeouts: ReturnType<typeof setTimeout>[] = [];

    PIPELINE_STAGES.forEach((stage, idx) => {
      accumulatedTime += stage.durationMs;
      if (idx < PIPELINE_STAGES.length - 1) {
        const t = setTimeout(() => {
          setCurrentStep(stage.step + 1);
        }, accumulatedTime);
        timeouts.push(t);
      }
    });

    return () => {
      timeouts.forEach((t) => clearTimeout(t));
    };
  }, [isAnalyzing]);

  if (!isAnalyzing) return null;

  // Compute progress percentage
  const progressPct = Math.min(
    95,
    Math.round(((currentStep - 1) / PIPELINE_STAGES.length) * 100) + 15
  );

  return (
    <div className="editorial-card rounded-md p-6 bg-white border-2 border-stone-800 shadow-md mb-8 animate-fadeIn">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-stone-200 mb-4 gap-3">
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping absolute" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 relative" />
          </div>
          <div>
            <span className="text-[10px] font-mono-data uppercase tracking-widest text-stone-500 font-bold block">
              Inference Core Active
            </span>
            <h3 className="font-editorial text-lg font-bold text-stone-900 leading-none">
              Deep Neural Deconstruction Pipeline
            </h3>
          </div>
        </div>

        {/* Live Elapsed Counter & Processor info */}
        <div className="flex items-center gap-3 font-mono-data text-xs text-stone-600 self-start sm:self-auto bg-stone-50 px-3 py-1.5 rounded border border-stone-200">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-stone-500" />
            <span>Elapsed: <strong className="text-stone-900">{elapsedSeconds}s</strong></span>
          </div>
          <span className="text-stone-300">•</span>
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-stone-500" />
            <span>Evidence analysis</span>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-[11px] font-mono-data text-stone-500 mb-1.5">
          <span>Overall Pipeline Execution</span>
          <span>Stage {currentStep} of {PIPELINE_STAGES.length} ({progressPct}%)</span>
        </div>
        <div className="w-full h-2 bg-stone-100 rounded-full overflow-hidden border border-stone-200">
          <div
            className="h-full bg-stone-900 transition-all duration-500 rounded-full"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Itemized 5-Stage Stepper Stream */}
      <div className="space-y-3">
        {PIPELINE_STAGES.map((stage) => {
          const isDone = currentStep > stage.step;
          const isActive = currentStep === stage.step;
          // queued state handled by else

          return (
            <div
              key={stage.step}
              className={`p-3 rounded border transition-all flex items-start justify-between gap-3 ${
                isActive
                  ? 'bg-stone-50 border-stone-800 shadow-xs ring-1 ring-stone-800'
                  : isDone
                  ? 'bg-emerald-50/40 border-emerald-200 text-stone-800'
                  : 'bg-white border-stone-200 opacity-60'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Status Indicator Icon */}
                <div className="mt-0.5 shrink-0">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : isActive ? (
                    <RotateCw className="w-4 h-4 text-stone-900 animate-spin" />
                  ) : (
                    <Circle className="w-4 h-4 text-stone-300" />
                  )}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono-data font-bold uppercase text-stone-500">
                      Stage 0{stage.step}:
                    </span>
                    <h4
                      className={`font-editorial text-sm font-bold ${
                        isActive ? 'text-stone-950 font-extrabold' : isDone ? 'text-stone-900' : 'text-stone-500'
                      }`}
                    >
                      {stage.title}
                    </h4>
                  </div>
                  <p className="text-xs font-sans text-stone-600 mt-0.5 leading-snug">
                    {stage.detail}
                  </p>
                </div>
              </div>

              {/* Model & Stage Badge */}
              <div className="shrink-0 text-right">
                <span
                  className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono-data border ${
                    isActive
                      ? 'bg-stone-900 text-white border-stone-900 font-semibold'
                      : isDone
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : 'bg-stone-100 text-stone-600 border-stone-200'
                  }`}
                >
                  {isDone ? 'Estimated stage' : isActive ? 'Active Inference...' : stage.model}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Informational Colophon */}
      <div className="mt-4 pt-3 border-t border-stone-100 flex items-center justify-between text-[11px] font-mono-data text-stone-500">
        <span className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-stone-400" />
          <span>Stage indicators estimate progress; the server confirms completion</span>
        </span>
        <span className="text-stone-400">Review evidence and model limitations</span>
      </div>
    </div>
  );
};
