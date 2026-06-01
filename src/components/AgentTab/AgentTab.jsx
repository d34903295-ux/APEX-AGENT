// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — AGENT TAB
// Dedicated view for AI Agent Interaction and Settings
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import { motion } from 'framer-motion';

const AgentTab = ({ messages, isTyping, latestId, aiConfig, mcpStatus, voice }) => {
  return (
    <motion.div
      className="agent-tab"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}
    >
      <div className="hud-card hud-corners-full" style={{ padding: '24px', textAlign: 'center', marginTop: '16px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(0, 209, 255, 0.1)', border: '1px solid rgba(0, 209, 255, 0.3)', marginBottom: '16px' }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#00D1FF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a4 4 0 0 1 4 4v2h2.5A2.5 2.5 0 0 1 21 10.5v7a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5v-7A2.5 2.5 0 0 1 5.5 8H8V6a4 4 0 0 1 4-4z"/>
            <path d="M8 8v2"/>
            <path d="M16 8v2"/>
            <path d="M12 14v4"/>
            <path d="M9 14h6"/>
          </svg>
        </div>
        <h2 style={{ fontFamily: "'Fira Code', monospace", fontSize: '18px', color: '#EDEDEF', margin: '0 0 8px 0' }}>APEX INTELLIGENCE</h2>
        <p style={{ fontSize: '12px', color: '#8A8F98', margin: '0 0 24px 0' }}>
          Modelo actual: {aiConfig?.model?.split('/').pop() || 'Desconocido'}<br/>
          Estado de Voz: {voice.isListening ? 'Escuchando' : 'Standby'}
        </p>
        
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button 
            onClick={voice.toggleListening}
            style={{ padding: '8px 16px', background: voice.isListening ? 'rgba(248, 113, 113, 0.1)' : 'rgba(0, 209, 255, 0.1)', border: `1px solid ${voice.isListening ? '#f87171' : '#00D1FF'}`, color: voice.isListening ? '#f87171' : '#00D1FF', borderRadius: '6px', fontSize: '12px', fontWeight: 'bold', cursor: 'pointer' }}
          >
            {voice.isListening ? 'DETENER MICRÓFONO' : 'ACTIVAR MICRÓFONO'}
          </button>
        </div>

        <div style={{ marginTop: '24px', textAlign: 'left', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ fontSize: '10px', color: '#8A8F98', marginBottom: '8px', letterSpacing: '0.05em' }}>VOZ DEL AGENTE</div>
          <select 
            value={voice.selectedVoiceURI || ''} 
            onChange={(e) => voice.setSelectedVoiceURI(e.target.value)}
            style={{ 
              width: '100%', padding: '8px', background: 'rgba(255,255,255,0.05)', 
              border: '1px solid rgba(255,255,255,0.1)', color: '#EDEDEF', 
              borderRadius: '6px', fontSize: '12px', outline: 'none', cursor: 'pointer'
            }}
          >
            {voice.availableVoices?.map(v => (
              <option key={v.voiceURI} value={v.voiceURI} style={{ background: '#0a0a0c' }}>
                {v.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginTop: '16px', textAlign: 'left', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ fontSize: '10px', color: '#8A8F98', marginBottom: '8px', letterSpacing: '0.05em' }}>SKILLS INYECTADAS (AGENTIC_SEEK & PIPECAT)</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {['Agentic Reasoning', 'Pipecat Voice Interrupt', 'Autonomous Execution', 'Market Intel'].map(skill => (
              <span key={skill} style={{ fontSize: '11px', background: 'rgba(52, 211, 153, 0.1)', color: '#34d399', padding: '4px 8px', borderRadius: '4px', border: '1px solid rgba(52, 211, 153, 0.2)' }}>
                ✓ {skill}
              </span>
            ))}
          </div>
        </div>
      </div>
      
      <div className="hud-card" style={{ flex: 1, padding: '16px', overflowY: 'auto' }}>
        <div className="hud-section-header">LOGS DEL SISTEMA AGENTE</div>
        <div style={{ fontFamily: "'Fira Code', monospace", fontSize: '11px', color: '#8A8F98', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {messages.map(m => (
            <div key={m.id} style={{ paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <strong style={{ color: m.role === 'assistant' ? '#34D399' : '#00D1FF' }}>{m.role === 'assistant' ? 'AI' : 'USER'}:</strong> {m.content}
            </div>
          ))}
          {messages.length === 0 && <div>Esperando instrucciones del Director...</div>}
        </div>
      </div>
    </motion.div>
  );
};

export default AgentTab;
