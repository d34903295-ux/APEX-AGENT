// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — QUICK ACTIONS
// 5 real AI-powered prompt buttons
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import './IntelligenceTerminal.scss';

const QUICK_PROMPTS = [
  { label: '¿Cómo está mi portafolio?',          prompt: '¿Cómo está mi portafolio hoy? Dame un resumen completo de exposición y balance.', icon: '📊' },
  { label: '¿Estoy expuesto al DXY?',             prompt: '¿Estoy expuesto al DXY? Analiza el impacto del Dollar Index en mis posiciones actuales.', icon: '💵' },
  { label: 'Analiza mi riesgo',                   prompt: 'Analiza mi riesgo actual con detalle: concentración, VaR estimado, Sharpe ratio y recomendaciones de hedging.', icon: '🛡️' },
  { label: '¿Debo comprar BTC?',                  prompt: '¿Debo comprar Bitcoin ahora? Analiza el precio actual de BTC vs mi costo promedio y dame una recomendación táctica.', icon: '₿' },
  { label: 'Resumen ejecutivo del día',           prompt: 'Dame un resumen ejecutivo completo del día: estado del portafolio, mercado, riesgo y acción recomendada para las próximas 24h.', icon: '📋' },
];

const QuickActions = ({ onAction, isDemo = false, onAddFunds }) => {
  return (
    <div className="quick-actions">
      <div className="quick-actions__scroll">
        {isDemo && (
          <button
            className="quick-actions__pill"
            onClick={() => onAddFunds?.(10000)}
            id="quick-action-demo-funds"
            style={{ background: 'rgba(251,191,36,0.15)', border: '1px solid rgba(251,191,36,0.4)', color: '#FBBF24' }}
          >
            <span className="quick-actions__icon">💰</span>
            +$10,000 Demo USD
          </button>
        )}
        {QUICK_PROMPTS.map((p, i) => (
          <button
            key={i}
            className="quick-actions__pill"
            onClick={() => onAction(p.prompt)}
            id={`quick-action-${i}`}
            title={p.prompt}
          >
            <span className="quick-actions__icon">{p.icon}</span>
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default QuickActions;
