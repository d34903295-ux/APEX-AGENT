// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — LEDGER
// Transaction record from Wallbit API
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { generateInvoice } from '../../utils/invoice';
import { loadLocalData } from '../../services/wallbit';
import './Ledger.scss';

const COLOR_MAP = {
  emerald: '#34D399',
  cyan: '#00D1FF',
  gold: '#FBBF24',
  rose: '#f87171',
};

const Ledger = ({ transactions = [], onSimulate: onNewTx, prefs = {} }) => {
  const { privateMode, currency = 'USD', exchangeRate = 1 } = prefs;
  const safeTx = Array.isArray(transactions) ? transactions : [];

  const formatAmount = (val) => {
    if (privateMode) return val >= 0 ? '+ ●●●●' : '− ●●●●';
    if (val === undefined || val === null || isNaN(val)) return '$0.00';
    const rate = isNaN(exchangeRate) ? 1 : exchangeRate;
    const converted = Math.abs(val) * rate;
    const prefix = val >= 0 ? '+' : '−';
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
    }).format(converted);
    return `${prefix} ${formatted}`;
  };

  return (
    <motion.div
      className="ledger"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.5 }}
    >
      <div className="hud-section-header" style={{ padding: `0 16px` }}>
        <span>WALLBIT TRANSACTION RECORD</span>
        <button className="ledger__sim-btn" onClick={onNewTx}>
          + NUEVA OPERACIÓN
        </button>
      </div>

      <div className="ledger__list">
        <AnimatePresence initial={false}>
          {safeTx.slice(0, 8).map((tx, i) => (
            <motion.div
              key={tx.id}
              className="ledger__item"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3, delay: i * 0.03 }}
              layout
            >
              <div
                className="ledger__dot"
                style={{ background: COLOR_MAP[tx.color] || COLOR_MAP.cyan }}
              />
              <div className="ledger__info">
                <div className="ledger__desc">{tx.desc}</div>
                <div className="ledger__meta">
                  <span className="ledger__type">{tx.type}</span>
                  <span className="ledger__date">{tx.date}</span>
                </div>
              </div>
              <div className={`ledger__amount mono ${tx.amount >= 0 ? 'text-emerald' : 'text-rose'}`}>
                {formatAmount(tx.amount)}
              </div>
              <button 
                className="ledger__invoice-btn"
                onClick={() => generateInvoice(
                  tx,
                  prefs.accountName || 'Usuario',
                  tx.id?.startsWith('demo') || tx.id?.startsWith('paper') || /demo|paper/i.test(tx.status || ''),
                  loadLocalData('market') || [],
                )}
                title="Descargar Factura Electrónica"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#8A8F98',
                  cursor: 'pointer',
                  marginLeft: '8px',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: '4px',
                }}
                onMouseEnter={e => { e.currentTarget.style.color = '#EDEDEF'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                onMouseLeave={e => { e.currentTarget.style.color = '#8A8F98'; e.currentTarget.style.background = 'transparent'; }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" x2="12" y1="15" y2="3" />
                </svg>
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      
      <div style={{ padding: '0 16px 16px 16px' }}>
        <button style={{
          width: '100%',
          padding: '10px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          borderRadius: '8px',
          color: '#8A8F98',
          fontSize: '11px',
          fontFamily: "'Fira Sans', sans-serif",
          fontWeight: '500',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }}
        onMouseEnter={(e) => {
          e.target.style.background = 'rgba(255, 255, 255, 0.06)';
          e.target.style.color = '#EDEDEF';
        }}
        onMouseLeave={(e) => {
          e.target.style.background = 'rgba(255, 255, 255, 0.03)';
          e.target.style.color = '#8A8F98';
        }}
        >
          Ver historial completo
        </button>
      </div>
    </motion.div>
  );
};

export default Ledger;
