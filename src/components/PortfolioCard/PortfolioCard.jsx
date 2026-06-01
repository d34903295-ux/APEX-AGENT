// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — PORTFOLIO CARD
// Total assets with HUD corners, waveform, and scan button
// ════════════════════════════════════════════════════════════════════

import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { CornerBrackets } from '../HUD/HUD';
import './PortfolioCard.scss';

const Waveform = ({ active }) => {
  const bars = useRef([12, 20, 32, 16, 26, 8, 14]);
  const [heights, setHeights] = useState(bars.current);

  useEffect(() => {
    if (!active) {
      setHeights(bars.current);
      return;
    }
    const interval = setInterval(() => {
      setHeights(bars.current.map(() => 4 + Math.random() * 32));
    }, 120);
    return () => clearInterval(interval);
  }, [active]);

  return (
    <div className="waveform">
      {heights.map((h, i) => (
        <div
          key={i}
          className="waveform__bar"
          style={{
            height: `${h}px`,
            opacity: 0.3 + (i % 3) * 0.2,
          }}
        />
      ))}
    </div>
  );
};

const PortfolioCard = ({ portfolio = {}, onScan, prefs = {}, isDemo }) => {
  const [displayValue, setDisplayValue] = useState(0);
  const [scanning, setScanning] = useState(false);
  const { totalValue = 0, cash = 0, equity = 0, crypto = 0, dayChangePct = 0, paperCash = 0, spendableCash } = portfolio || {};
  const { privateMode, currency = 'USD', exchangeRate = 1 } = prefs;
  const availableCash = spendableCash ?? (isDemo ? cash : (paperCash > 0 ? paperCash : cash));
  const showPaperHint = !isDemo && paperCash > 0;

  // ─── COUNT UP ANIMATION ─────────────────────────────────────
  useEffect(() => {
    const duration = 1500;
    const start = performance.now();
    const startVal = displayValue;

    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(startVal + (totalValue - startVal) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [totalValue]);

  // ─── HANDLE SCAN ────────────────────────────────────────────
  const handleScan = () => {
    setScanning(true);
    setTimeout(() => setScanning(false), 3500);
    if (onScan) onScan();
  };

  const formatCurrency = (val) => {
    if (privateMode) return '●●●●';
    if (val === undefined || val === null || isNaN(val)) return '$0.00';
    const rate = isNaN(exchangeRate) ? 1 : exchangeRate;
    const converted = val * rate;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
    }).format(converted);
  };

  return (
    <motion.div
      className="portfolio-card hud-card hud-corners-full hud-top-glow"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
    >
      <CornerBrackets />

      {/* Radar Sweep */}
      {scanning && <div className="hud-radar-sweep" />}

      {/* Scan Button */}
      <button className="portfolio-card__scan" onClick={handleScan}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        ESCANEAR
      </button>

      {/* Label */}
      <div className="hud-label" style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>VALOR TOTAL DE LA CARTERA {currency !== 'USD' ? `(${currency})` : ''}</span>
          {isDemo && (
            <span style={{ background: 'rgba(251,191,36,0.2)', color: '#FBBF24', fontSize: '10px', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(251,191,36,0.3)', letterSpacing: '0.05em' }}>DEMO</span>
          )}
        </div>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </div>

      {/* Total Value + 24H Change */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <div className="portfolio-card__value mono">
          {formatCurrency(displayValue)}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px', fontFamily: "'Fira Code', monospace" }}>
          <span style={{ color: portfolio.dayChangePct >= 0 ? '#34D399' : '#f87171', fontSize: '12px', fontWeight: '600' }}>
            {dayChangePct >= 0 ? '+' : ''}{(dayChangePct || 0).toFixed(2)}%
          </span>
          <span style={{ color: '#8A8F98', fontSize: '10px' }}>(24H)</span>
        </div>
      </div>

      {/* Grid: Cash / Equity / Crypto */}
      <div className="portfolio-card__grid">
        <div className="portfolio-card__col">
          <div className="portfolio-card__dot portfolio-card__dot--gold" />
          <span className="portfolio-card__col-label">{showPaperHint ? 'EFECTIVO (PAPER)' : isDemo ? 'EFECTIVO (DEMO)' : 'EFECTIVO'}</span>
          <span className="portfolio-card__col-value mono">{formatCurrency(availableCash)}</span>
        </div>
        <div className="portfolio-card__col">
          <div className="portfolio-card__dot portfolio-card__dot--cyan" />
          <span className="portfolio-card__col-label">ACCIONES</span>
          <span className="portfolio-card__col-value mono">{formatCurrency(equity)}</span>
        </div>
        <div className="portfolio-card__col">
          <div className="portfolio-card__dot portfolio-card__dot--emerald" />
          <span className="portfolio-card__col-label">CRIPTOS</span>
          <span className="portfolio-card__col-value mono">{formatCurrency(crypto)}</span>
        </div>
      </div>

      {/* Waveform */}
      <Waveform active={scanning} />
    </motion.div>
  );
};

export default PortfolioCard;
