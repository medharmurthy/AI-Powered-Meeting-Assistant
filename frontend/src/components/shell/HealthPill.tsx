import React, { useEffect, useState } from 'react';
import type { HealthResponse } from '../../api/types';
import { fetchHealth } from '../../api/client';

export const HealthPill: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const data = await fetchHealth();
        if (mounted) setHealth(data);
      } catch (e) {
        // quiet error on health check failure
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (!health) {
    return null;
  }

  const sttOk = !!health.stt.model;
  const refinerOk = health.llm.reachable && health.llm.refiner.installed;
  const docOk = health.llm.reachable && health.llm.documenter.installed;

  return (
    <div className="health-group" role="status" aria-label="Engine health status">
      <div className="health-pill" title={`STT Engine: ${health.stt.model} (${health.stt.device})`}>
        <span className={`health-dot ${sttOk ? 'ok' : 'alert'}`} />
        <span>Whisper</span>
      </div>
      <div className="health-pill" title={`Refiner: ${health.llm.refiner.model}`}>
        <span className={`health-dot ${refinerOk ? 'ok' : 'alert'}`} />
        <span>{health.llm.refiner.model.split(':')[0]}</span>
      </div>
      <div className="health-pill" title={`Documenter: ${health.llm.documenter.model}`}>
        <span className={`health-dot ${docOk ? 'ok' : 'alert'}`} />
        <span>{health.llm.documenter.model.split(':')[0]}</span>
      </div>
    </div>
  );
};
