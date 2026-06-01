// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — ASSETS TAB
// Full holdings view with PnL, donut chart, composition bars
// Simulados (Demo / Paper) + Wallbit Live
// ════════════════════════════════════════════════════════════════════

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { computePortfolioComposition } from '../../utils/paperPortfolio';
import './AssetsTab.scss';

const fmt = (v, dec = 2) => {
  if (v === undefined || v === null || isNaN(v)) return '$0.00';
  return `$${Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec })}`;
};
const fmtPct = (v) => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(2)}%`;

const DonutChart = ({ segments }) => {
  const r = 54, cx = 64, cy = 64;
  const circum = 2 * Math.PI * r;
  let cumulative = 0;
  return (
    <svg width="128" height="128" className="donut-chart">
      {segments.map((seg, i) => {
        const dash = (seg.pct / 100) * circum;
        const offset = circum - cumulative * circum / 100;
        cumulative += seg.pct;
        return (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={seg.color} strokeWidth="12"
            strokeDasharray={`${dash} ${circum - dash}`}
            strokeDashoffset={offset}
            style={{ transform: 'rotate(-90deg)', transformOrigin: 'center' }}
          />
        );
      })}
      <text x={cx} y={cy - 4} textAnchor="middle" className="donut-label-value">Portfolio</text>
      <text x={cx} y={cy + 14} textAnchor="middle" className="donut-label-sub">Composición</text>
    </svg>
  );
};

const HoldingBadge = ({ h, isDemo }) => {
  if (h.isDemo || isDemo) {
    return <span className="assets-badge assets-badge--demo">DEMO</span>;
  }
  if (h.isPaper) {
    return <span className="assets-badge assets-badge--paper">PAPER</span>;
  }
  if (h.isLive) {
    return <span className="assets-badge assets-badge--live">LIVE</span>;
  }
  return null;
};

const HoldingsTable = ({ rows, onBuySell, emptyHint }) => {
  if (!rows.length) {
    return (
      <div className="assets-empty">
        <p>{emptyHint || 'Sin posiciones en esta sección.'}</p>
      </div>
    );
  }

  return (
    <div className="assets-table-wrap">
      <table className="assets-table">
        <thead>
          <tr>
            <th>ACTIVO</th>
            <th>QTY</th>
            <th>COSTO PROM.</th>
            <th>PRECIO</th>
            <th>TOTAL</th>
            <th>PnL</th>
            <th>ACCIÓN</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((h, i) => {
            const pnl = h.pnl ?? 0;
            const pnlPct = h.pnlPct ?? (h.costAvg > 0 ? ((h.priceNow - h.costAvg) / h.costAvg) * 100 : 0);
            const positive = pnl >= 0;
            return (
              <motion.tr key={h.id || `${h.symbol}-${i}`} className="assets-row"
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}>
                <td>
                  <div className="assets-asset">
                    <span className="assets-symbol">{h.symbol}</span>
                    <span className="assets-name">{h.name || h.symbol}</span>
                    <HoldingBadge h={h} />
                  </div>
                </td>
                <td className="mono">{(h.qty || 0).toLocaleString(undefined, { maximumFractionDigits: 6 })}</td>
                <td className="mono">{fmt(h.costAvg)}</td>
                <td className={`mono ${positive ? 'text-emerald' : 'text-rose'}`}>{fmt(h.priceNow)}</td>
                <td className="mono">{fmt(h.total)}</td>
                <td>
                  <div className={`assets-pnl ${positive ? 'assets-pnl--up' : 'assets-pnl--down'}`}>
                    <span>{positive ? '+' : ''}{fmt(pnl)}</span>
                    <span className="assets-pnl__pct">{fmtPct(pnlPct)}</span>
                  </div>
                </td>
                <td>
                  <div className="assets-actions">
                    <button className="assets-btn assets-btn--buy" onClick={() => onBuySell?.(h.symbol || h, 'COMPRA')}>COMPRAR</button>
                    <button className="assets-btn assets-btn--sell" onClick={() => onBuySell?.(h.symbol || h, 'VENTA')}>VENDER</button>
                  </div>
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const AssetsTab = ({ portfolio, holdings, onBuySell, isDemo, marketData = [] }) => {
  const simRows = useMemo(
    () => (holdings || []).filter((h) => isDemo || h.isPaper || h.isDemo),
    [holdings, isDemo]
  );
  const liveRows = useMemo(
    () => (isDemo ? [] : (holdings || []).filter((h) => !h.isPaper && !h.isDemo)),
    [holdings, isDemo]
  );

  const composition = useMemo(
    () => computePortfolioComposition(portfolio, holdings, { isDemo }),
    [portfolio, holdings, isDemo]
  );

  const { total, segments } = composition;
  const spendable = portfolio?.spendableCash ?? portfolio?.paperCash ?? portfolio?.cash ?? 0;

  return (
    <div className="assets-tab">
      <motion.div className="assets-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="hud-section-header">
          <span>COMPOSICIÓN DEL PORTAFOLIO</span>
          {(isDemo || portfolio?.paperCash > 0) && (
            <span className="hud-label" style={{ color: isDemo ? '#FBBF24' : '#00D1FF' }}>
              {isDemo ? 'MODO DEMO' : 'INCLUYE PAPER'}
            </span>
          )}
        </div>

        <div className="assets-composition">
          <DonutChart segments={segments} />
          <div className="assets-composition__legend">
            {segments.map((s) => (
              <div key={s.label} className="assets-legend-item">
                <div className="assets-legend-dot" style={{ background: s.color }} />
                <span className="assets-legend-label">{s.label}</span>
                <span className="assets-legend-pct">{s.pct.toFixed(1)}%</span>
              </div>
            ))}
            <div className="assets-legend-total">
              <span>TOTAL</span>
              <span>{fmt(total)}</span>
            </div>
            <div className="assets-legend-total" style={{ marginTop: 6, fontSize: 11, color: '#8A8F98' }}>
              <span>Disponible para operar</span>
              <span style={{ color: isDemo ? '#FBBF24' : '#00D1FF' }}>{fmt(spendable)}</span>
            </div>
          </div>
        </div>

        <div className="assets-bars">
          {segments.map((s) => (
            <div key={s.label} className="assets-bar-wrap">
              <div className="assets-bar-label">
                <span>{s.label}</span><span>{s.pct.toFixed(1)}%</span>
              </div>
              <div className="assets-bar-track">
                <motion.div className="assets-bar-fill"
                  style={{ background: s.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${s.pct}%` }}
                  transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                />
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* ─── SIMULADOS (Demo / Paper) — prioridad ─── */}
      {(isDemo || simRows.length > 0 || portfolio?.paperCash > 0) && (
        <motion.div className="assets-card assets-card--sim" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
          <div className="hud-section-header">
            <span>ACTIVOS SIMULADOS ({simRows.length})</span>
            <span className="hud-label" style={{ color: '#00D1FF' }}>
              {isDemo ? 'CUENTA DEMO' : 'FONDOS PAPER'}
            </span>
          </div>
          <p className="assets-section-hint">
            Las compras con fondos simulados aparecen aquí al instante. El saldo paper se descuenta en cada COMPRA.
          </p>
          <HoldingsTable
            rows={simRows}
            onBuySell={onBuySell}
            emptyHint="Aún no compraste activos simulados. Usa COMPRA en el modal o el terminal de voz."
          />
        </motion.div>
      )}

      {/* ─── WALLBIT LIVE ─── */}
      <motion.div className="assets-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}>
        <div className="hud-section-header">
          <span>ACTIVOS WALLBIT LIVE ({liveRows.length})</span>
          <span className="hud-label" style={{ color: '#8A8F98' }}>API REAL</span>
        </div>
        <HoldingsTable
          rows={liveRows}
          onBuySell={onBuySell}
          emptyHint="Sin posiciones reales en Wallbit (o precios aún cargando)."
        />
      </motion.div>
    </div>
  );
};

export default AssetsTab;
