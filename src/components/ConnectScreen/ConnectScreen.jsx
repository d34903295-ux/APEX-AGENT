// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — CONNECT SCREEN
// Real Wallbit API key validation
// ════════════════════════════════════════════════════════════════════

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AmbientBlobs, Scanlines } from '../HUD/HUD';
import { validateWallbitKey, saveApiKey } from '../../services/wallbit';
import './ConnectScreen.scss';

const ERROR_LOG = (msg) => ({
  text: `[ERROR] ${msg || 'No se pudo conectar con Wallbit.'}`,
  type: 'error',
});

const ConnectScreen = ({ onConnect }) => {
  const [apiKey,  setApiKey]  = useState('');
  const [aiUrl,   setAiUrl]   = useState('https://openrouter.ai/api/v1/chat/completions');
  const [aiModel, setAiModel] = useState('anthropic/claude-sonnet-4-5');
  const [aiKey,   setAiKey]   = useState('');
  const [status,  setStatus]  = useState('idle');
  const [logs,    setLogs]    = useState([]);
  const [progress, setProgress] = useState(0);
  const [logoVisible, setLogoVisible] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => setLogoVisible(true), 300);
    try {
      const savedAiKey = localStorage.getItem('apex_ai_key');
      const savedAiUrl = localStorage.getItem('apex_ai_url');
      const savedAiModel = localStorage.getItem('apex_ai_model');
      if (savedAiKey) setAiKey(savedAiKey);
      if (savedAiUrl) setAiUrl(savedAiUrl);
      if (savedAiModel) setAiModel(savedAiModel);
    } catch {}
    return () => clearTimeout(t);
  }, []);

  const handleConnect = async () => {
    const cleanKey = apiKey.trim().replace(/[\u200B-\u200D\uFEFF]/g, '');
    if (!cleanKey) { inputRef.current?.focus(); return; }
    // Ya no bloqueamos si no hay aiKey, usamos WebLLM como fallback

    setStatus('connecting');
    
    const initialLogs = !aiKey.trim() 
      ? [
          { text: '[00:00:00] No se detectó API Key de IA. Se inicializará WebLLM localmente.', type: 'normal' },
          { text: '[00:00:01] Validando API Key con Wallbit (api.wallbit.io)...', type: 'normal' }
        ]
      : [{ text: '[00:00:01] Validando API Key con Wallbit (api.wallbit.io)...', type: 'normal' }];
      
    setLogs(initialLogs);
    setProgress(10);

    const result = await validateWallbitKey(cleanKey);

    if (!result.valid) {
      setLogs(prev => [
        ...prev,
        { text: '[00:00:02] ✗ Wallbit rechazó la key', type: 'error' },
        ERROR_LOG(result.error),
      ]);
      setStatus('error');
      setProgress(0);
      return;
    }

    setLogs(prev => [...prev, { text: '[00:00:02] ✓ API Key válida — cargando portafolio...', type: 'success' }]);
    setProgress(40);

    if (result.mcpConnected) {
      setLogs(prev => [...prev, { text: `[00:00:03] ✓ MCP conectado — ${(result.mcpTools || []).length} tools`, type: 'success' }]);
    } else {
      setLogs(prev => [...prev, { text: '[00:00:03] MCP offline — usando REST directo', type: 'normal' }]);
    }
    setProgress(70);

    setLogs(prev => [...prev, { text: '[00:00:04] ✓ APEX SYSTEM ONLINE — WELCOME, DIRECTOR', type: 'success' }]);
    setProgress(100);
    setStatus('success');
    saveApiKey(cleanKey);

    try {
      localStorage.setItem('apex_ai_key', aiKey.trim());
      localStorage.setItem('apex_ai_url', aiUrl.trim());
      localStorage.setItem('apex_ai_model', aiModel.trim());
      localStorage.setItem('apex_login_ts', new Date().toISOString());
    } catch {}

    await new Promise(r => setTimeout(r, 600));
    onConnect(cleanKey, result.profile, false, {
      url: aiUrl.trim(), model: aiModel.trim(), key: aiKey.trim(),
    });
  };

  const handleReset = () => {
    setStatus('idle'); setLogs([]); setProgress(0);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  return (
    <motion.div className="connect-screen">
      <AmbientBlobs />
      <Scanlines />
      <motion.div
        className="connect-content"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      >
        <AnimatePresence>
          {logoVisible && (
            <motion.div className="connect-logo" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1 }}>
              <div className="connect-logo__icon">
                <svg viewBox="0 0 40 40" fill="none">
                  <path d="M20 4L36 34H4L20 4Z" stroke="#00D1FF" strokeWidth="1.5" fill="none" />
                  <path d="M20 12L28 30H12L20 12Z" stroke="#00D1FF" strokeWidth="0.8" fill="rgba(0,209,255,0.08)" />
                  <circle cx="20" cy="22" r="2" fill="#00D1FF" />
                </svg>
              </div>
              <h1 className="connect-logo__title">APEX</h1>
              <p className="connect-logo__sub">FINANCIAL INTELLIGENCE</p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="connect-gateway-label">WALLBIT API KEY</div>
        <p className="connect-demo-hint">
          Wallbit Dashboard → <strong>Agents</strong> → Create agent → permisos <strong>read</strong> + <strong>trade</strong>.
          Copia la key completa (empieza con wlb_live_).
        </p>
        <div className={`connect-input-wrap ${status === 'error' ? 'connect-input-wrap--error' : ''}`}>
          <input ref={inputRef} type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleConnect()}
            placeholder="wlb_live_••••••••••••••••" className="connect-input"
            disabled={status === 'connecting' || status === 'success'} id="api-key-input" autoComplete="off" />
        </div>

        <div className="connect-gateway-label" style={{ marginTop: 24 }}>AI GATEWAY (OpenRouter · OpenAI · Groq)</div>
        <p className="connect-demo-hint">
          Recomendamos usar una API de OpenRouter para mayor velocidad. Si dejas la API Key en blanco, el sistema descargará y utilizará <strong>WebLLM (IA Local)</strong> como respaldo (la descarga inicial puede tardar varios minutos y requerir espacio en caché).
        </p>

        <div className="connect-input-wrap" style={{ marginTop: 10 }}>
          <input type="text" value={aiUrl} onChange={e => setAiUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleConnect()}
            placeholder="https://openrouter.ai/api/v1/chat/completions" className="connect-input"
            disabled={status === 'connecting' || status === 'success'} autoComplete="off" />
        </div>

        <div className="connect-input-wrap" style={{ marginTop: 8 }}>
          <input type="text" value={aiModel} onChange={e => setAiModel(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleConnect()}
            placeholder="anthropic/claude-sonnet-4-5" className="connect-input"
            disabled={status === 'connecting' || status === 'success'} autoComplete="off" />
        </div>

        <div className="connect-input-wrap" style={{ marginTop: 8 }}>
          <input type="password" value={aiKey} onChange={e => setAiKey(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleConnect()}
            placeholder="sk-or-v1-••••••••••••••••••" className="connect-input"
            disabled={status === 'connecting' || status === 'success'} autoComplete="off" />
        </div>

        {status === 'error' ? (
          <button className="connect-btn connect-btn--reset" onClick={handleReset}>REINTENTAR CONEXIÓN</button>
        ) : (
          <>
            <button className="connect-btn" onClick={handleConnect} disabled={status === 'connecting' || status === 'success'} id="connect-btn">
              {status === 'connecting' ? 'CONECTANDO...' : status === 'success' ? '✓ CONECTADO' : 'CONECTAR AL SISTEMA'}
            </button>
            <button
              className="connect-btn"
              onClick={() => {
                try {
                  localStorage.setItem('apex_ai_key', aiKey.trim());
                  localStorage.setItem('apex_ai_url', aiUrl.trim());
                  localStorage.setItem('apex_ai_model', aiModel.trim());
                } catch {}
                saveApiKey('demo');
                onConnect('demo', { name: 'DEMO', email: 'demo@apex.local' }, true, {
                  url: aiUrl.trim(), model: aiModel.trim(), key: aiKey.trim(),
                });
              }}
              id="demo-btn"
              style={{ background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.4)', color: '#FBBF24', marginTop: 8 }}
            >
              🎮 ENTRAR EN MODO DEMO ($10,000 USD virtuales)
            </button>
          </>
        )}

        <AnimatePresence>
          {logs.length > 0 && (
            <motion.div className="connect-terminal"
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.4 }}>
              {logs.map((log, i) => (
                <motion.div key={i} className={`connect-terminal__line connect-terminal__line--${log.type}`}
                  initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.25, delay: i * 0.04 }}>
                  {log.text}
                </motion.div>
              ))}
              {progress > 0 && (
                <div className="connect-progress">
                  <div className="connect-progress__bar" style={{ width: `${progress}%` }} />
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
};

export default ConnectScreen;
