// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — HOLDINGS TABLE
// Portfolio holdings with live price coloring and P&L
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import { motion } from 'framer-motion';
import './Holdings.scss';

const Holdings = ({ holdings = [], prefs = {} }) => {
  const { privateMode, currency = 'USD', exchangeRate = 1 } = prefs;
  const safeHoldings = Array.isArray(holdings) ? holdings : [];

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

  const getPnl = (cost, current) => {
    if (!cost || cost <= 0) return 0;
    return ((current - cost) / cost) * 100;
  };

  return (
    <motion.div
      className="holdings"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.4 }}
    >
      <div className="hud-section-header" style={{ padding: `0 16px` }}>
        <span>PORTAFOLIO HOLDINGS (WALLBIT LIVE)</span>
      </div>

      <div className="holdings__table-wrap">
        <table className="holdings__table">
          <thead>
            <tr>
              <th>ACTIVO</th>
              <th>COSTO PROM.</th>
              <th>PRECIO HOY</th>
              <th>P/L %</th>
              <th>TOTAL</th>
            </tr>
          </thead>
          <tbody>
            {safeHoldings.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: '#8A8F98', fontSize: 12 }}>
                  Sin posiciones abiertas — usa el terminal de voz o + NUEVA OPERACIÓN
                </td>
              </tr>
            ) : safeHoldings.map((h, i) => {
              const symbol = h?.symbol || '?';
              const qty = h.qty ?? h.amount ?? 0;
              const priceNow = h.priceNow ?? h.currentPrice ?? 0;
              const costAvg = h.costAvg ?? priceNow;
              const rowTotal = h.total ?? h.value ?? qty * priceNow;
              const pnlPct = getPnl(costAvg, priceNow);
              const isUp = pnlPct >= 0;
              return (
                <motion.tr
                  key={h.id || `${symbol}-${i}`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 * i, duration: 0.3 }}
                  className="holdings__row"
                >
                  <td>
                    <div className="holdings__asset">
                      {h.logoUrl ? (
                        <img src={h.logoUrl} alt="" className="holdings__logo" width={24} height={24} />
                      ) : (
                        <div className="holdings__logo-placeholder">{symbol.charAt(0)}</div>
                      )}
                      <div>
                        <div className="holdings__symbol">{symbol}</div>
                        <div className="holdings__name">{h.name}</div>
                      </div>
                    </div>
                  </td>
                  <td className="holdings__num mono">{formatCurrency(costAvg)}</td>
                  <td className={`holdings__num mono`}>
                    {formatCurrency(priceNow)}
                  </td>
                  <td>
                    <div className={`holdings__pnl ${isUp ? 'holdings__pnl--up' : 'holdings__pnl--down'}`}>
                      {isUp ? '+' : ''}{pnlPct.toFixed(2)}%
                    </div>
                  </td>
                  <td className="holdings__num holdings__total mono">{formatCurrency(rowTotal)}</td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default Holdings;
