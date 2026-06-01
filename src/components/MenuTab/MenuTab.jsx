// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — MENU TAB
// Profile, AI Config, Display Prefs, Session, About
// ════════════════════════════════════════════════════════════════════

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { clearApiKey, clearLocalData, saveLocalData, loadLocalData } from '../../services/wallbit';
import { MCP_TOOLS } from '../../services/wallbitMcp';
import McpStatus from '../McpStatus/McpStatus';
import './MenuTab.scss';

const Toggle = ({ value, onChange, id }) => (
  <button id={id} className={`menu-toggle ${value ? 'menu-toggle--on' : ''}`} onClick={() => onChange(!value)} aria-pressed={value}>
    <div className="menu-toggle__thumb" />
  </button>
);

const MenuTab = ({ apiKey, profile, aiConfig, onLogout, mcpStatus, mcpTools, transport, onMcpRefresh, lastSync, isDemo, onAddLivePaperFunds, livePaperBalance, livePaperEnabled: livePaperProp, onPaperToggle }) => {
  const savedPrefs = loadLocalData('prefs') || {};

  const [voiceEnabled,   setVoiceEnabled]   = useState(savedPrefs.voiceEnabled ?? true);
  const [continuousListen, setContinuous]   = useState(savedPrefs.continuousListen ?? false);
  const [textInputEnabled, setTextInputEnabled] = useState(savedPrefs.textInputEnabled ?? false);
  const [lang,            setLang]          = useState(savedPrefs.lang ?? 'es-ES');
  const [riskAlerts,      setRiskAlerts]    = useState(savedPrefs.riskAlerts ?? true);
  const [privateMode,     setPrivateMode]   = useState(savedPrefs.privateMode ?? false);
  const [fontSize,        setFontSize]      = useState(savedPrefs.fontSize ?? 'normal');
  const [accountName,     setAccountName]   = useState(savedPrefs.accountName || 'Director');
  const [currency,        setCurrency]      = useState(savedPrefs.currency ?? 'USD');
  const [exchangeRate,    setExchangeRate]  = useState(savedPrefs.exchangeRate ?? 1);
  const [useLocalCurrency,setUseLocalCurrency] = useState(savedPrefs.useLocalCurrency ?? false);
  const [rateLoading,     setRateLoading]   = useState(false);
  const [saved,           setSaved]         = useState(false);
  const [livePaperEnabled, setLivePaperEnabled] = useState(livePaperProp ?? savedPrefs.livePaperEnabled ?? false);

  useEffect(() => {
    if (livePaperProp !== undefined) setLivePaperEnabled(livePaperProp);
  }, [livePaperProp]);
  const [customPaperAmt,   setCustomPaperAmt]   = useState('');

  const CURRENCIES = [
    { code: 'USD', label: 'USD — Dólar Americano', symbol: '$' },
    { code: 'ARS', label: 'ARS — Peso Argentino', symbol: '$' },
    { code: 'EUR', label: 'EUR — Euro', symbol: '€' },
    { code: 'BRL', label: 'BRL — Real Brasileño', symbol: 'R$' },
    { code: 'MXN', label: 'MXN — Peso Mexicano', symbol: '$' },
    { code: 'CLP', label: 'CLP — Peso Chileno', symbol: '$' },
    { code: 'COP', label: 'COP — Peso Colombiano', symbol: '$' },
    { code: 'GBP', label: 'GBP — Libra Esterlina', symbol: '£' },
    { code: 'JPY', label: 'JPY — Yen Japonés', symbol: '¥' },
    { code: 'CAD', label: 'CAD — Dólar Canadiense', symbol: 'CA$' },
    { code: 'AUD', label: 'AUD — Dólar Australiano', symbol: 'A$' },
    { code: 'CHF', label: 'CHF — Franco Suizo', symbol: 'Fr' },
  ];

  // Fetch live exchange rate when currency changes
  useEffect(() => {
    if (currency === 'USD') { setExchangeRate(1); return; }
    setRateLoading(true);
    fetch(`https://api.exchangerate-api.com/v4/latest/USD`)
      .then(r => r.json())
      .then(data => {
        const rate = data?.rates?.[currency];
        if (rate) setExchangeRate(rate);
      })
      .catch(() => {
        // Fallback hardcoded approximate rates
        const fallback = { ARS: 1000, EUR: 0.92, BRL: 5.0, MXN: 17, CLP: 900, COP: 4000, GBP: 0.79, JPY: 150, CAD: 1.36, AUD: 1.53, CHF: 0.88 };
        setExchangeRate(fallback[currency] || 1);
      })
      .finally(() => setRateLoading(false));
  }, [currency]);

  const loginTs = (() => {
    try { return localStorage.getItem('apex_login_ts'); } catch { return null; }
  })();

  const maskedKey = apiKey
    ? `${apiKey.slice(0, 8)}••••••••${apiKey.slice(-4)}`
    : '••••••••';

  const prefs = { 
    voiceEnabled, 
    continuousListen, 
    textInputEnabled,
    lang, 
    riskAlerts, 
    privateMode, 
    fontSize, 
    accountName, 
    currency: useLocalCurrency ? currency : 'USD', 
    exchangeRate: useLocalCurrency ? exchangeRate : 1,
    useLocalCurrency,
    livePaperEnabled
  };

  const savePrefs = () => {
    saveLocalData('prefs', prefs);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    // Dispatch custom event so App can react
    window.dispatchEvent(new CustomEvent('apex-prefs-change', { detail: prefs }));
  };

  const handleExport = () => {
    const data = {
      portfolio: loadLocalData('portfolio'),
      holdings:  loadLocalData('holdings'),
      transactions: loadLocalData('transactions'),
      prefs,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = `apex-portfolio-${Date.now()}.json`;
    a.click(); URL.revokeObjectURL(url);
  };

  const handleLogout = () => {
    clearApiKey();
    ['portfolio','holdings','transactions','chat_history','market','prefs'].forEach(clearLocalData);
    try {
      localStorage.removeItem('apex_ai_key');
      localStorage.removeItem('apex_ai_url');
      localStorage.removeItem('apex_ai_model');
      localStorage.removeItem('apex_login_ts');
    } catch {}
    onLogout?.();
  };

  const initials = accountName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  return (
    <div className="menu-tab">

      {/* ─── MCP GATEWAY ────────────────────────── */}
      <motion.div className="menu-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="hud-section-header"><span>WALLBIT MCP GATEWAY</span></div>
        <McpStatus status={mcpStatus} tools={mcpTools} lastSync={lastSync} compact={false} />
        <div className="menu-mcp-tools">
          {(mcpTools?.length ? mcpTools : MCP_TOOLS.map(t => t.name)).map(name => {
            const meta = MCP_TOOLS.find(t => t.name === name);
            return (
              <div key={name} className="menu-mcp-tool">
                <span>{meta?.icon || '◆'}</span>
                <span>{meta?.label || name}</span>
              </div>
            );
          })}
        </div>
        <div className="menu-info-row" style={{ marginTop: 8 }}>
          <span>Transporte activo:</span>
          <span className="mono" style={{ color: transport === 'mcp' ? '#00D1FF' : '#FBBF24' }}>
            {transport === 'mcp' ? 'MCP (mcp.wallbit.io)' : 'REST API'}
          </span>
        </div>
        <button className="menu-action-btn" style={{ marginTop: 10 }} onClick={onMcpRefresh} type="button">
          ↻ RECONECTAR MCP
        </button>
      </motion.div>

      {/* ─── PERFIL ─────────────────────────────── */}
      <motion.div className="menu-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="hud-section-header"><span>PERFIL DE CUENTA</span></div>
        <div className="menu-profile">
          <div className="menu-avatar">{initials || 'AP'}</div>
          <div className="menu-profile__fields">
            <div className="menu-field">
              <label className="menu-label">Nombre de cuenta</label>
              <input className="menu-input" value={accountName} onChange={e => setAccountName(e.target.value)} />
            </div>
            <div className="menu-field" style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <label className="menu-label" style={{ marginBottom: 0 }}>Usar moneda local (Conversión)</label>
                <Toggle id="toggle-currency" value={useLocalCurrency} onChange={setUseLocalCurrency} />
              </div>
              
              {useLocalCurrency && (
                <div style={{ padding: '8px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                  <label className="menu-label">Seleccionar Moneda</label>
                  <select className="menu-select" value={currency} onChange={e => setCurrency(e.target.value)}>
                    {CURRENCIES.map(c => (
                      <option key={c.code} value={c.code}>{c.label}</option>
                    ))}
                  </select>
                  {currency !== 'USD' && (
                    <div style={{ fontSize: 10, color: rateLoading ? '#FBBF24' : '#34D399', fontFamily: "'Fira Code', monospace", marginTop: 4 }}>
                      {rateLoading ? '... cargando tipo de cambio' : `1 USD = ${exchangeRate.toLocaleString('es-AR', { maximumFractionDigits: 2 })} ${currency}`}
                    </div>
                  )}
                </div>
              )}
            </div>
            {profile?.email && (
              <div className="menu-field">
                <label className="menu-label">Email</label>
                <div className="menu-readonly">{profile.email}</div>
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* ─── AI CONFIG ──────────────────────────── */}
      <motion.div className="menu-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="hud-section-header"><span>CONFIGURACIÓN APEX AI</span></div>
        <div className="menu-rows">
          <div className="menu-row">
            <div><div className="menu-row__title">Respuesta por voz (TTS)</div><div className="menu-row__sub">APEX habla sus respuestas</div></div>
            <Toggle id="toggle-voice" value={voiceEnabled} onChange={setVoiceEnabled} />
          </div>
          <div className="menu-row">
            <div><div className="menu-row__title">Escucha continua</div><div className="menu-row__sub">Mic se reactiva automáticamente</div></div>
            <Toggle id="toggle-continuous" value={continuousListen} onChange={setContinuous} />
          </div>
          <div className="menu-row">
            <div><div className="menu-row__title">Habilitar chat de texto</div><div className="menu-row__sub">Input manual en la consola</div></div>
            <Toggle id="toggle-text-input" value={textInputEnabled} onChange={setTextInputEnabled} />
          </div>
          <div className="menu-row">
            <div><div className="menu-row__title">Idioma de voz</div></div>
            <select className="menu-select-sm" value={lang} onChange={e => setLang(e.target.value)}>
              <option value="es-ES">Español (ES)</option>
              <option value="es-AR">Español (AR)</option>
              <option value="es-MX">Español (MX)</option>
              <option value="en-US">English (US)</option>
              <option value="en-GB">English (UK)</option>
              <option value="pt-BR">Português (BR)</option>
              <option value="fr-FR">Français</option>
            </select>
          </div>
          <div className="menu-row">
            <div><div className="menu-row__title">Alertas de riesgo automáticas</div><div className="menu-row__sub">Aviso si portafolio cae &gt;2%</div></div>
            <Toggle id="toggle-risk" value={riskAlerts} onChange={setRiskAlerts} />
          </div>
          <div className="menu-row">
            <div><div className="menu-row__title">Modelo activo</div><div className="menu-row__sub">{aiConfig?.model || 'No configurado'}</div></div>
          </div>
        </div>
      </motion.div>

      {/* ─── DISPLAY PREFS ──────────────────────── */}
      <motion.div className="menu-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <div className="hud-section-header"><span>PREFERENCIAS DE DISPLAY</span></div>
        <div className="menu-rows">
          <div className="menu-row">
            <div><div className="menu-row__title">Modo privado</div><div className="menu-row__sub">Oculta valores con ●●●●</div></div>
            <Toggle id="toggle-private" value={privateMode} onChange={setPrivateMode} />
          </div>
          {isDemo && (
            <div className="menu-row" style={{ background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 8, padding: '8px 12px' }}>
              <div><div className="menu-row__title" style={{ color: '#FBBF24' }}>🎮 Modo Demo Activo</div><div className="menu-row__sub">Operaciones ficticias — sin dinero real</div></div>
              <span style={{ color: '#FBBF24', fontSize: 12, fontFamily: "'Fira Code', monospace" }}>SIM</span>
            </div>
          )}
          {/* ─── LIVE PAPER MONEY (only visible in LIVE mode) ── */}
          {!isDemo && (
            <div style={{ marginTop: 8 }}>
              <div className="menu-row" style={{ background: 'rgba(0,209,255,0.06)', border: '1px solid rgba(0,209,255,0.18)', borderRadius: 8, padding: '8px 12px' }}>
                <div>
                  <div className="menu-row__title" style={{ color: livePaperEnabled ? '#00D1FF' : '#34D399' }}>
                    {livePaperEnabled ? '💰 Modo simulación activo' : '✓ Modo real (Wallbit Live)'}
                  </div>
                  <div className="menu-row__sub">
                    {livePaperEnabled
                      ? 'Solo ves fondos y trades paper. Desactiva para volver al portafolio real de Wallbit.'
                      : 'Desactivado = datos 100% reales. Activa para practicar con cash ficticio sin mezclar con tu saldo real.'}
                  </div>
                </div>
                <Toggle
                  id="toggle-live-paper"
                  value={livePaperEnabled}
                  onChange={(val) => {
                    setLivePaperEnabled(val);
                    onPaperToggle?.(val);
                  }}
                />
              </div>
              {livePaperEnabled && (
                <div style={{ background: 'rgba(0,209,255,0.04)', borderRadius: 8, padding: 12, marginTop: 6, border: '1px solid rgba(0,209,255,0.12)' }}>
                  <div style={{ fontSize: 10, color: '#8A8F98', letterSpacing: '0.08em', marginBottom: 6 }}>BALANCE PAPER ACTUAL</div>
                  <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "'Fira Code', monospace", color: '#00D1FF', marginBottom: 10 }}>
                    ${(livePaperBalance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })} USD
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                    {[1000, 5000, 10000, 25000].map(amt => (
                      <button key={amt}
                        style={{ flex: 1, minWidth: 60, padding: '6px 4px', background: 'rgba(0,209,255,0.12)', border: '1px solid rgba(0,209,255,0.3)', borderRadius: 6, color: '#00D1FF', fontSize: 11, fontWeight: 600, cursor: 'pointer', fontFamily: "'Fira Code', monospace" }}
                        onClick={() => onAddLivePaperFunds?.(amt)}>
                        +${(amt / 1000).toFixed(0)}K
                      </button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      type="number" min="100" step="100"
                      placeholder="Monto personalizado..."
                      value={customPaperAmt}
                      onChange={e => setCustomPaperAmt(e.target.value)}
                      style={{ flex: 1, padding: '7px 10px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6, color: '#E8EAF0', fontSize: 12, outline: 'none' }}
                    />
                    <button
                      disabled={!customPaperAmt || parseFloat(customPaperAmt) <= 0}
                      onClick={() => { onAddLivePaperFunds?.(parseFloat(customPaperAmt)); setCustomPaperAmt(''); }}
                      style={{ padding: '7px 14px', background: '#00D1FF', border: 'none', borderRadius: 6, color: '#020203', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                      ＋ ADD
                    </button>
                  </div>
                  <div style={{ fontSize: 9, color: '#8A8F98', marginTop: 6, fontFamily: "'Fira Code', monospace" }}>⚠ Los fondos paper se muestran en el Ledger pero no son reales.</div>
                </div>
              )}
            </div>
          )}
          <div className="menu-row">
            <div><div className="menu-row__title">Tamaño de fuente</div></div>
            <div className="menu-radio-group">
              {['small','normal','large'].map(s => (
                <button key={s} className={`menu-radio ${fontSize === s ? 'menu-radio--active' : ''}`} onClick={() => setFontSize(s)}>
                  {s === 'small' ? 'A' : s === 'normal' ? 'Aa' : 'AA'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* ─── SAVE BUTTON ────────────────────────── */}
      <button className="menu-save-btn" onClick={savePrefs} id="save-prefs-btn">
        {saved ? '✓ GUARDADO' : 'GUARDAR CONFIGURACIÓN'}
      </button>

      {/* ─── SESSION & SECURITY ─────────────────── */}
      <motion.div className="menu-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <div className="hud-section-header"><span>SESIÓN Y SEGURIDAD</span></div>
        <div className="menu-rows">
          <div className="menu-info-row"><span>Conectado como:</span><span className="mono">{maskedKey}</span></div>
          {loginTs && (
            <div className="menu-info-row">
              <span>Sesión activa desde:</span>
              <span className="mono">{new Date(loginTs).toLocaleString('es-AR')}</span>
            </div>
          )}
        </div>
        <div className="menu-actions">
          <button className="menu-action-btn menu-action-btn--export" onClick={handleExport} id="export-btn">
            ↓ EXPORTAR DATOS JSON
          </button>
          <button className="menu-action-btn menu-action-btn--logout" onClick={handleLogout} id="logout-btn">
            ⏻ CERRAR SESIÓN
          </button>
        </div>
      </motion.div>

      {/* ─── ABOUT ──────────────────────────────── */}
      <motion.div className="menu-section menu-about" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
        <div className="menu-about__logo">▲</div>
        <div className="menu-about__name">APEX Financial v1.0.0</div>
        <div className="menu-about__powered">Powered by Wallbit API · OpenRouter · MCP Protocol</div>
        <div className="menu-about__links">
          <a href="https://wallbit.io" target="_blank" rel="noreferrer">Documentación</a>
          <span>·</span>
          <a href="https://openrouter.ai" target="_blank" rel="noreferrer">OpenRouter</a>
          <span>·</span>
          <a href="https://mcp.wallbit.io" target="_blank" rel="noreferrer">MCP</a>
        </div>
      </motion.div>
    </div>
  );
};

export default MenuTab;
