// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — MAIN APPLICATION
// 3-column Bloomberg layout (desktop) / single column (mobile)
// Real voice, real AI, real portfolio data
// ════════════════════════════════════════════════════════════════════

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

// ─── HUD Layer ──────────────────────────────────────────────────────
import { Scanlines, AmbientBlobs, GridBackground } from './components/HUD/HUD';

// ─── Screens ────────────────────────────────────────────────────────
import ConnectScreen from './components/ConnectScreen/ConnectScreen';

// ─── Shared Components ──────────────────────────────────────────────
import Dashboard         from './components/Dashboard/Dashboard';
import TickerBar         from './components/TickerBar/TickerBar';
import PortfolioCard     from './components/PortfolioCard/PortfolioCard';
import MarketPulse       from './components/MarketPulse/MarketPulse';
import IntelligenceTerminal from './components/IntelligenceTerminal/IntelligenceTerminal';
import QuickActions      from './components/IntelligenceTerminal/QuickActions';
import Holdings          from './components/Holdings/Holdings';
import Ledger            from './components/Ledger/Ledger';
import VoiceConsole      from './components/VoiceConsole/VoiceConsole';
import SimModal          from './components/SimModal/SimModal';
import NavBar            from './components/NavBar/NavBar';
import McpStatus         from './components/McpStatus/McpStatus';

// ─── Tab Views ──────────────────────────────────────────────────────
import AssetsTab  from './components/AssetsTab/AssetsTab';
import MarketTab  from './components/MarketTab/MarketTab';
import MenuTab    from './components/MenuTab/MenuTab';
import AgentTab   from './components/AgentTab/AgentTab';
import ModeBanner from './components/ModeBanner/ModeBanner';

// ─── Hooks ──────────────────────────────────────────────────────────
import { useWallbitAPI } from './hooks/useWallbitAPI';
import { useVoice }      from './hooks/useVoice';
import { useApexAI }     from './hooks/useApexAI';

// ─── Services ───────────────────────────────────────────────────────
import { loadApiKey } from './services/wallbit';
import { generateInvoice } from './utils/invoice';

// ─── Styles ─────────────────────────────────────────────────────────
import './styles/main.scss';

// ════════════════════════════════════════════════════════════════════
// BOOT SEQUENCE
// ════════════════════════════════════════════════════════════════════
const BOOT_LINES = [
  'APEX SYSTEM INITIALIZING...',
  'LOADING WALLBIT PORTFOLIO BRAIN...',
  'MCP PROTOCOL ACTIVE...',
  'SYNCING MARKET FEEDS...',
  'VOICE ENGINE READY',
  'ALL SYSTEMS NOMINAL — WELCOME, DIRECTOR',
];

const BootSequence = ({ onComplete }) => {
  const [lines, setLines] = useState([]);
  const [done, setDone]   = useState(false);

  useEffect(() => {
    let i = 0;
    const timer = setInterval(() => {
      if (i < BOOT_LINES.length) { setLines(prev => [...prev, BOOT_LINES[i]]); i++; }
      else { clearInterval(timer); setTimeout(() => { setDone(true); setTimeout(onComplete, 600); }, 400); }
    }, 180);
    return () => clearInterval(timer);
  }, [onComplete]);

  return (
    <motion.div
      initial={{ opacity: 1 }}
      animate={{ opacity: done ? 0 : 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      style={{ position: 'fixed', inset: 0, background: '#020203', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 150 }}
    >
      <div style={{ maxWidth: 360, width: '100%', padding: '0 24px' }}>
        {lines.map((line, i) => (
          <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}
            style={{ fontFamily: "'Fira Code', monospace", fontSize: '10px', lineHeight: '2.2',
              color: i === lines.length - 1 && i === BOOT_LINES.length - 1 ? '#34D399' : '#8A8F98', letterSpacing: '0.05em' }}>
            {'>'} {line}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

// ════════════════════════════════════════════════════════════════════
// MAIN APP
// ════════════════════════════════════════════════════════════════════
const App = () => {
  const [screen,      setScreen]      = useState('connect');
  const [apiKey,      setApiKey]      = useState(null);
  const [profile,     setProfile]     = useState(null);
  const [aiConfig,    setAiConfig]    = useState(null);
  const [activeTab,   setActiveTab]   = useState('home');
  const [simOpen,     setSimOpen]     = useState(false);
  const [simPreset,   setSimPreset]   = useState(null);
  const [latestAiId,  setLatestAiId]  = useState(null);
  const [isDesktop,   setIsDesktop]   = useState(window.innerWidth >= 768);
  const [prefs,       setPrefs]       = useState({});
  const [isDemo,      setIsDemo]      = useState(false);

  // ─── Responsive breakpoint ──────────────────────────────────────
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)');
    const handler = (e) => setIsDesktop(e.matches);
    mq.addEventListener('change', handler);
    setIsDesktop(mq.matches);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // ─── Load persisted prefs ───────────────────────────────────────
  useEffect(() => {
    try { const p = localStorage.getItem('apex_prefs'); if (p) setPrefs(JSON.parse(p)); } catch {}
    window.addEventListener('apex-prefs-change', (e) => setPrefs(e.detail));
    return () => window.removeEventListener('apex-prefs-change', () => {});
  }, []);

  // ─── Auto-login if session exists ───────────────────────────────
  useEffect(() => {
    const stored = loadApiKey();
    let aiKey, aiUrl, aiModel;
    try {
      aiKey   = localStorage.getItem('apex_ai_key');
      aiUrl   = localStorage.getItem('apex_ai_url');
      aiModel = localStorage.getItem('apex_ai_model');
    } catch {}
    if (stored && aiKey) {
      setApiKey(stored);
      setIsDemo(stored === 'demo');
      setAiConfig({ url: aiUrl || 'https://openrouter.ai/api/v1/chat/completions', model: aiModel || 'anthropic/claude-sonnet-4-5', key: aiKey });
      setScreen('boot');
    }
  }, []);

  // ─── Data hooks ─────────────────────────────────────────────────
  const livePaperEnabled = !!prefs.livePaperEnabled && !isDemo;
  const dataMode = isDemo ? 'demo' : (livePaperEnabled ? 'paper' : 'real');
  const wallbit = useWallbitAPI(apiKey, isDemo, livePaperEnabled);

  const portfolioData = {
    totalValue:    wallbit.portfolio.totalValue,
    cash:          wallbit.portfolio.cash,
    equity:        wallbit.portfolio.equity,
    crypto:        wallbit.portfolio.crypto,
    dayChange:     wallbit.portfolio.dayChange,
    dayChangePct:  wallbit.portfolio.dayChangePct,
    transactions:  wallbit.transactions,
  };

  const ai = useApexAI(portfolioData, aiConfig, wallbit.marketData, {
    transport: wallbit.transport,
    mcpStatus: wallbit.mcpStatus,
    mcpTools: wallbit.mcpTools,
  });

  // ─── Voice Setup (To avoid TDZ & Circular Dependencies) ─────────
  const speakRef = useRef(null);

  // ─── SFX ────────────────────────────────────────────────────────
  const playBeep = useCallback(() => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.1);
    } catch (e) {}
  }, []);

  // ─── Open sim with preset (before processConversation — evita TDZ) ─
  const openSimWithPreset = useCallback((asset, type, amount = '') => {
    setSimPreset({ asset, type, amount });
    setSimOpen(true);
  }, []);

  // ─── Voice Order Mocking & Chat ─────────────────────────────────
  const processConversation = useCallback(async (text) => {
    const lower = text.toLowerCase();
    
    // Intercept Voice Commands
    if (lower.includes('comprar ') || lower.includes('vender ') || lower.includes('buy ') || lower.includes('sell ')) {
      playBeep();
      let asset = 'USD';
      if (lower.includes('bitcoin') || lower.includes('btc')) asset = 'BTC';
      else if (lower.includes('ethereum') || lower.includes('eth')) asset = 'ETH';
      else if (lower.includes('apple') || lower.includes('aapl')) asset = 'AAPL';
      else if (lower.includes('tesla') || lower.includes('tsla')) asset = 'TSLA';
      
      const type = (lower.includes('comprar') || lower.includes('buy')) ? 'TRADE_BUY' : 'TRADE_SELL';
      openSimWithPreset(asset, type, '');
      if (prefs.voiceEnabled !== false && speakRef.current) speakRef.current(`Abriendo terminal de ejecución para ${type === 'TRADE_BUY' ? 'comprar' : 'vender'} ${asset}. Por favor confirme la orden.`);
      return;
    }

    playBeep();
    const response = await ai.processMessage(text, (toolArgs) => {
      // Callback for AI tools
      const type = toolArgs.type === 'COMPRA' ? 'TRADE_BUY' : 'TRADE_SELL';
      openSimWithPreset(toolArgs.asset, type, toolArgs.amountUsd);
    });
    
    if (response) {
      setTimeout(() => {
        setLatestAiId(`ai_${Date.now() - 1}`);
      }, 50);
      if (prefs.voiceEnabled !== false && speakRef.current) speakRef.current(response);
    }
  }, [ai, prefs, playBeep, openSimWithPreset]);

  // ─── Voice ──────────────────────────────────────────────────────
  const handleTranscript = useCallback(async (text) => {
    await processConversation(text);
    // Auto-detect risk alerts
    if (prefs.riskAlerts && wallbit.portfolio.dayChangePct < -2) {
      setTimeout(() => {
        if (speakRef.current) speakRef.current(`⚠ Alerta: su portafolio cayó ${Math.abs(wallbit.portfolio.dayChangePct || 0).toFixed(2)}% hoy.`);
      }, 1000);
    }
  }, [processConversation, prefs, wallbit.portfolio.dayChangePct]);

  const voice = useVoice({
    onTranscript: handleTranscript,
    lang: prefs.lang || 'es-ES',
    continuous: !!prefs.continuousListen,
  });

  // Assign speak function to ref for stable access
  useEffect(() => {
    speakRef.current = voice.speak;
  }, [voice.speak]);

  // ─── Connect ────────────────────────────────────────────────────
  const handleConnect = (key, prof, demo, aiCfg) => {
    setApiKey(key || 'demo'); setProfile(prof); setAiConfig(aiCfg);
    setIsDemo(!!demo);
    setScreen('boot');
  };

  // ─── Logout ─────────────────────────────────────────────────────
  const handleLogout = () => {
    setApiKey(null); setProfile(null); setAiConfig(null);
    setScreen('connect'); setActiveTab('home');
  };

  // ─── Transaction (real Wallbit API) ───────────────────────────────
  const [txLoading, setTxLoading] = useState(false);
  const [txError, setTxError]     = useState(null);

  const handleSimConfirm = async (tx) => {
    setTxLoading(true);
    setTxError(null);
    try {
      const record = await wallbit.submitTransaction(tx);
      setSimOpen(false);
      setSimPreset(null);

      const invoiceTx = record && typeof record === 'object' ? record : {
        ...tx,
        id: `TX-${Date.now().toString().slice(-8)}`,
        date: new Date().toISOString(),
        total: Math.abs(parseFloat(tx.amountUsd ?? tx.amount ?? 0)),
        amountUsd: Math.abs(parseFloat(tx.amountUsd ?? tx.amount ?? 0)),
      };
      const isSim = dataMode !== 'real' || invoiceTx.id?.includes('demo') || invoiceTx.id?.includes('paper');
      generateInvoice(invoiceTx, prefs.accountName || 'Usuario', isSim, wallbit.marketData);

      setTimeout(() => {
        processConversation(`He confirmado la ejecución de la orden: ${tx.type} de $${Math.abs(tx.amount).toLocaleString()} USD${tx.asset ? ` en ${tx.asset}` : ''}.`);
      }, 400);
    } catch (err) {
      setTxError(err.message);
    } finally {
      setTxLoading(false);
    }
  };

  // ─── Keyboard shortcuts ─────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key === 'm') { e.preventDefault(); voice.toggleListening(); }
      if (e.ctrlKey && e.key === 't') { e.preventDefault(); setSimOpen(true); }
      if (e.key === 'Escape') { setSimOpen(false); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [voice]);

  // ─── Private mode formatter ─────────────────────────────────────
  const pv = (val) => prefs.privateMode ? '●●●●' : val;

  // ────────────────────────────────────────────────────────────────
  // RENDER
  // ────────────────────────────────────────────────────────────────
  // ─── Font size class ────────────────────────────────────────────
  const fontSizeClass = prefs.fontSize === 'small' ? 'apex-font-sm' : prefs.fontSize === 'large' ? 'apex-font-lg' : '';

  return (
    <>
      <GridBackground />
      <AmbientBlobs />

      <AnimatePresence mode="sync">
        {screen === 'connect' && <ConnectScreen key="connect" onConnect={handleConnect} />}
        {screen === 'boot'    && (
          <BootSequence
            key="boot"
            onComplete={() => setScreen('dashboard')}
          />
        )}

        {screen === 'dashboard' && (
          <motion.div
            key="dashboard"
            className={`apex-app ${fontSizeClass}`}
            initial={false}
            animate={{ opacity: 1 }}
            style={{ opacity: 1 }}
          >
            <Scanlines />

            {/* Content — switches at 768px */}
            {isDesktop ? (
              <div className="apex-desktop">
                {/* Far Left Sidebar */}
                <div className="apex-sidebar">
                  <div className="apex-sidebar__top">
                    {/* Voice Mic inside Sidebar (matches design) */}
                    <button className={`apex-sidebar__mic ${voice.isListening ? 'active' : ''}`} onClick={voice.toggleListening}>
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                        <line x1="12" x2="12" y1="19" y2="22" />
                      </svg>
                    </button>
                    <NavBar activeTab={activeTab} onTabChange={setActiveTab} vertical />
                  </div>
                  <div className="apex-sidebar__bottom">
                    <div className="apex-sidebar__user">Director</div>
                    <div className="apex-sidebar__brand">Apex Financial</div>
                    <div className="apex-sidebar__status"><span className="dot"></span> Online</div>
                  </div>
                </div>

                {/* Main View Area */}
                <div className="apex-main">
                  {/* Header */}
                  <Dashboard mcpStatus={wallbit.mcpStatus} transport={wallbit.transport} />
                  <ModeBanner dataMode={dataMode} onOpenSettings={() => setActiveTab('menu')} />
                  {wallbit.error && (
                    <div style={{ margin: '8px 16px', padding: '8px 12px', background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 6, fontSize: 11, color: '#f87171' }}>
                      ⚠ Wallbit: {wallbit.error}
                    </div>
                  )}
                  <TickerBar marketData={wallbit.marketData} />

                  <div className="apex-columns">
                    {/* Left Column */}
                    <div className="apex-col apex-col--left">
                      <McpStatus status={wallbit.mcpStatus} tools={wallbit.mcpTools} lastSync={wallbit.lastSync} />
                      <PortfolioCard portfolio={wallbit.portfolio} onScan={() => processConversation('Analiza mi riesgo actual con detalle: concentración, VaR, Sharpe ratio y recomendaciones.')} dataMode={dataMode} prefs={prefs} />
                      <MarketPulse marketData={wallbit.marketData} />
                      <QuickActions onAction={processConversation} dataMode={dataMode} onAddFunds={dataMode === 'demo' ? wallbit.addDemoFunds : undefined} />
                    </div>

                    {/* Center Column */}
                    <div className="apex-col apex-col--center">
                      {activeTab === 'home' && (
                        <>
                          <IntelligenceTerminal messages={ai.messages} isTyping={ai.isTyping} latestId={latestAiId} aiConfig={aiConfig} mcpStatus={wallbit.mcpStatus} />
                          <VoiceConsole isListening={voice.isListening} isSpeaking={voice.isSpeaking}
                            isSupported={voice.isSupported} lastError={voice.lastError} onToggleMic={voice.toggleListening}
                            onSendText={processConversation} onOpenTx={() => setSimOpen(true)} textInputEnabled={prefs.textInputEnabled} />
                        </>
                      )}
                      {activeTab === 'agent'  && <AgentTab messages={ai.messages} isTyping={ai.isTyping} latestId={latestAiId} aiConfig={aiConfig} mcpStatus={wallbit.mcpStatus} voice={voice} />}
                      {activeTab === 'assets' && <AssetsTab portfolio={wallbit.portfolio} holdings={wallbit.holdings} onBuySell={openSimWithPreset} dataMode={dataMode} marketData={wallbit.marketData} />}
                      {activeTab === 'market' && <MarketTab apiKey={apiKey} />}
                      {activeTab === 'menu'   && (
                        <MenuTab apiKey={apiKey} profile={profile} aiConfig={aiConfig} onLogout={handleLogout}
                          mcpStatus={wallbit.mcpStatus} mcpTools={wallbit.mcpTools} transport={wallbit.transport}
                          onMcpRefresh={wallbit.checkMcp} lastSync={wallbit.lastSync} isDemo={isDemo}
                          onAddLivePaperFunds={wallbit.addLivePaperFunds}
                          livePaperBalance={wallbit.portfolio?.paperCash || 0}
                          livePaperEnabled={livePaperEnabled}
                          onPaperToggle={(enabled) => {
                            const next = { ...prefs, livePaperEnabled: enabled };
                            setPrefs(next);
                            try { localStorage.setItem('apex_prefs', JSON.stringify(next)); } catch {}
                            window.dispatchEvent(new CustomEvent('apex-prefs-change', { detail: next }));
                          }} />
                      )}
                    </div>

                    {/* Right Column */}
                    <div className="apex-col apex-col--right">
                      <Holdings holdings={wallbit.holdings} prefs={prefs} />
                      <Ledger transactions={wallbit.transactions} onSimulate={() => setSimOpen(true)} prefs={prefs} />

                      {/* APEX VOICE STATUS */}
                      <div className="hud-card" style={{ marginTop: 'auto', marginBottom: 16 }}>
                        <div className="hud-section-header">APEX VOICE STATUS</div>
                        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', fontFamily: "'Fira Code', monospace" }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#EDEDEF' }}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34D399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                              Micrófono
                            </div>
                            <span style={{ color: voice.isListening ? '#34D399' : '#8A8F98' }}>{voice.isListening ? 'Activo' : 'Standby'}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', fontFamily: "'Fira Code', monospace" }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#EDEDEF' }}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34D399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                              Conexión
                            </div>
                            <span style={{ color: '#34D399' }}>Estable</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', fontFamily: "'Fira Code', monospace" }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#EDEDEF' }}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34D399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                              IA Service
                            </div>
                            <span style={{ color: '#34D399' }}>Operativo</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', fontFamily: "'Fira Code', monospace" }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#EDEDEF' }}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34D399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                              MCP Sync
                            </div>
                            <span style={{ color: wallbit.mcpStatus === 'connected' ? '#34D399' : '#f87171' }}>{wallbit.mcpStatus === 'connected' ? 'Sincronizado' : 'Error'}</span>
                          </div>
                          
                          <div style={{ marginTop: '8px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '9px', color: '#8A8F98', fontFamily: "'Fira Code', monospace" }}>
                            <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#34D399', boxShadow: '0 0 4px #34D399' }}></span>
                            Sistema APEX: Standby | Seguro | En tiempo real
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="apex-scroll">
                <ModeBanner dataMode={dataMode} onOpenSettings={() => setActiveTab('menu')} />
                {activeTab === 'home' && (
                  <>
                    <PortfolioCard portfolio={wallbit.portfolio} onScan={() => processConversation('Analiza mi riesgo actual con detalle.')} dataMode={dataMode} prefs={prefs} />
                    <MarketPulse marketData={wallbit.marketData} />
                    <IntelligenceTerminal messages={ai.messages} isTyping={ai.isTyping} latestId={latestAiId} aiConfig={aiConfig} mcpStatus={wallbit.mcpStatus} />
                    <QuickActions onAction={processConversation} dataMode={dataMode} onAddFunds={dataMode === 'demo' ? wallbit.addDemoFunds : undefined} />
                    <Holdings holdings={wallbit.holdings} prefs={prefs} />
                    <Ledger transactions={wallbit.transactions} onSimulate={() => setSimOpen(true)} prefs={prefs} />
                  </>
                )}
                {activeTab === 'agent'  && <AgentTab messages={ai.messages} isTyping={ai.isTyping} latestId={latestAiId} aiConfig={aiConfig} mcpStatus={wallbit.mcpStatus} voice={voice} />}
                {activeTab === 'assets' && <AssetsTab portfolio={wallbit.portfolio} holdings={wallbit.holdings} onBuySell={openSimWithPreset} dataMode={dataMode} marketData={wallbit.marketData} />}
                {activeTab === 'market' && <MarketTab apiKey={apiKey} />}
                {activeTab === 'menu'   && (
                  <MenuTab apiKey={apiKey} profile={profile} aiConfig={aiConfig} onLogout={handleLogout}
                    mcpStatus={wallbit.mcpStatus} mcpTools={wallbit.mcpTools} transport={wallbit.transport}
                    onMcpRefresh={wallbit.checkMcp} lastSync={wallbit.lastSync} isDemo={isDemo}
                    onAddLivePaperFunds={wallbit.addLivePaperFunds}
                    livePaperBalance={wallbit.portfolio?.paperCash || 0}
                    livePaperEnabled={livePaperEnabled}
                    onPaperToggle={(enabled) => {
                      const next = { ...prefs, livePaperEnabled: enabled };
                      setPrefs(next);
                      try { localStorage.setItem('apex_prefs', JSON.stringify(next)); } catch {}
                      window.dispatchEvent(new CustomEvent('apex-prefs-change', { detail: next }));
                    }} />
                )}

                <VoiceConsole isListening={voice.isListening} isSpeaking={voice.isSpeaking}
                  isSupported={voice.isSupported} lastError={voice.lastError} onToggleMic={voice.toggleListening}
                  onSendText={processConversation} onOpenTx={() => setSimOpen(true)} textInputEnabled={prefs.textInputEnabled} />
                <NavBar activeTab={activeTab} onTabChange={setActiveTab} />
              </div>
            )}

            {/* Transaction Modal */}
            <SimModal
              isOpen={simOpen}
              onClose={() => { setSimOpen(false); setSimPreset(null); setTxError(null); }}
              onConfirm={handleSimConfirm}
              preselectedAsset={simPreset?.asset}
              preselectedType={simPreset?.type}
              preselectedAmount={simPreset?.amount}
              apiKey={apiKey}
              marketData={wallbit.marketData}
              isLoading={txLoading}
              error={txError}
              dataMode={dataMode}
              spendableCash={wallbit.spendableCash}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default App;
