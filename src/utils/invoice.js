// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — INVOICE GENERATOR
// Generates a print-ready HTML invoice in a popup window
// ════════════════════════════════════════════════════════════════════

import {
  isBuyType,
  isSellType,
  isTradeType,
  isDepositType,
  isWithdrawType,
  getMarketItem,
} from './paperPortfolio';
import { loadLocalData } from '../services/wallbit';

/**
 * Normaliza cualquier transacción (COMPRA, TRADE_BUY, paper, demo) para factura coherente.
 */
export const normalizeInvoiceTx = (tx, marketData = []) => {
  if (!tx) return tx;

  const isBuy = isBuyType(tx.type);
  const isSell = isSellType(tx.type);
  const isTrade = isTradeType(tx.type);
  const isDeposit = isDepositType(tx.type) || isWithdrawType(tx.type) || (!isTrade && !isBuy && !isSell);

  let asset = (tx.asset && tx.asset !== 'USD') ? tx.asset : null;
  if (!asset && tx.desc) {
    const symMatch = tx.desc.match(/(?:COMPRA|VENTA|TRADE_BUY|TRADE_SELL|BUY|SELL)\s+([\d.,]+)\s+([A-Z]{2,6})/i)
      || tx.desc.match(/\b([A-Z]{2,6})\b\s*@/i)
      || tx.desc.match(/\b(BTC|ETH|SOL|BNB|AAPL|TSLA|NVDA|MSFT|GOOG|AMZN)\b/);
    if (symMatch) asset = symMatch[symMatch.length - 1];
  }

  const total = Math.abs(
    parseFloat(tx.total ?? tx.amountUsd ?? tx.amount ?? 0)
  ) || 0;

  let units = Math.abs(parseFloat(tx.units ?? tx.amountAsset ?? 0)) || 0;
  let price = parseFloat(tx.price ?? 0) || 0;

  const mItem = asset ? getMarketItem(marketData, asset) : null;
  if ((!price || price <= 0) && mItem?.price) price = Number(mItem.price);

  if (isTrade && asset) {
    if ((!price || price <= 0) && units > 0 && total > 0) price = total / units;
    if ((!units || units <= 0) && price > 0 && total > 0) units = total / price;
    if (price > 0 && units > 0 && total > 0) {
      const drift = Math.abs(price * units - total) / total;
      if (drift > 0.02) units = total / price;
    }
  }

  const typeDisplay = isBuy ? 'COMPRA' : isSell ? 'VENTA' : tx.type;
  const assetLabel = asset || (isDeposit ? 'USD' : '—');
  const assetName = tx.assetName || mItem?.name || assetLabel;

  let desc = tx.desc || '';
  if (!desc || /^\[PAPER\]\s*TRADE_/i.test(desc) || /^TRADE_(BUY|SELL)$/i.test(desc)) {
    if (isTrade && asset && price > 0 && units > 0) {
      desc = `${typeDisplay} de ${units.toLocaleString('en-US', { maximumFractionDigits: 6 })} ${asset} @ $${price.toLocaleString('en-US', { minimumFractionDigits: 2 })} USD`;
    } else if (isDeposit) {
      desc = isWithdrawType(tx.type) ? 'Retiro a cuenta checking' : 'Depósito a inversión';
    } else {
      desc = typeDisplay;
    }
  }

  return {
    ...tx,
    type: typeDisplay,
    asset: assetLabel,
    assetName,
    price: isTrade ? price : (isDeposit ? 1 : price),
    units: isTrade ? units : (isDeposit ? total : units),
    total,
    desc,
  };
};

export const generateInvoice = (tx, accountName = 'Usuario', isDemo = false, marketData = null) => {
  const market = marketData?.length ? marketData : (loadLocalData('market') || []);
  const normalized = normalizeInvoiceTx(tx, market);
  const isBuy = isBuyType(normalized.type);
  const isSell = isSellType(normalized.type);
  const isTrade = isTradeType(normalized.type);
  const isDeposit = !isTrade;

  const typeLabel = isBuy ? 'COMPRA DE ACTIVO' : isSell ? 'VENTA DE ACTIVO' : 'DEPÓSITO / TRANSFERENCIA';
  const dateStr = new Date(normalized.date || Date.now()).toLocaleString('es-ES', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  const fmt = (v, decimals = 2) => {
    const n = parseFloat(v);
    if (isNaN(n)) return '$0.00';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: decimals }).format(Math.abs(n));
  };

  const isPaper = /paper/i.test(normalized.status || '') || /\[PAPER\]/i.test(normalized.desc || '');
  const isSim = isDemo || isPaper || /demo/i.test(normalized.status || '') || /demo_/i.test(normalized.id || '');

  const txId = normalized.id || `TX-${Date.now().toString().slice(-10)}`;
  const total = Math.abs(parseFloat(normalized.total || 0));
  const price = parseFloat(normalized.price) || (isDeposit ? 1 : 0);
  const unitQty = parseFloat(normalized.units) || (isDeposit ? total : 0);
  const assetDisplay = normalized.assetName && normalized.assetName !== normalized.asset
    ? `${normalized.asset} — ${normalized.assetName}`
    : normalized.asset || 'USD';

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <title>Factura ${txId} — APEX Financial</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap');
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Inter',sans-serif;background:#fff;color:#0a0a0a;padding:48px;max-width:820px;margin:0 auto}
    @media print{body{padding:24px}}
    .invoice-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px;padding-bottom:24px;border-bottom:2px solid #0a0a0a}
    .brand{display:flex;flex-direction:column;gap:4px}
    .brand-name{font-size:28px;font-weight:700;letter-spacing:-0.5px}
    .brand-name span{color:#1a56db}
    .brand-sub{font-size:11px;color:#6b7280;font-family:'Fira Code',monospace;letter-spacing:0.05em}
    .invoice-meta{text-align:right}
    .invoice-type{font-size:22px;font-weight:700;letter-spacing:-0.3px;margin-bottom:4px}
    .invoice-id{font-family:'Fira Code',monospace;font-size:11px;color:#6b7280}
    .demo-badge{display:inline-block;background:#fef3c7;color:#92400e;font-size:10px;font-weight:600;padding:3px 8px;border-radius:4px;margin-top:6px;letter-spacing:0.05em}
    .section{margin-bottom:32px}
    .section-title{font-size:9px;font-weight:700;letter-spacing:0.12em;color:#6b7280;text-transform:uppercase;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid #e5e7eb}
    .info-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    .info-item label{display:block;font-size:9px;color:#9ca3af;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:2px}
    .info-item span{font-size:13px;font-weight:500;font-family:'Fira Code',monospace}
    .detail-table{width:100%;border-collapse:collapse}
    .detail-table th{font-size:9px;font-weight:700;letter-spacing:0.1em;color:#6b7280;text-transform:uppercase;text-align:left;padding:10px 16px;background:#f9fafb;border:1px solid #e5e7eb}
    .detail-table td{padding:14px 16px;border:1px solid #e5e7eb;font-size:13px}
    .detail-table td.mono{font-family:'Fira Code',monospace}
    .detail-table td.right{text-align:right}
    .detail-table tr:last-child td{background:#f9fafb}
    .total-row td{font-weight:700!important;font-size:15px!important;background:#0a0a0a!important;color:#fff!important;border-color:#0a0a0a!important}
    .status-badge{display:inline-flex;align-items:center;gap:6px;background:#d1fae5;color:#065f46;font-size:11px;font-weight:600;padding:6px 14px;border-radius:999px}
    .status-badge::before{content:'';display:inline-block;width:6px;height:6px;background:#10b981;border-radius:50%}
    .footer{margin-top:48px;padding-top:24px;border-top:1px solid #e5e7eb;text-align:center}
    .footer p{font-size:10px;color:#9ca3af;line-height:1.8}
    .type-badge{display:inline-flex;padding:4px 12px;border-radius:4px;font-size:11px;font-weight:700;letter-spacing:0.05em;background:${isBuy?'#dbeafe':isSell?'#fef3c7':'#d1fae5'};color:${isBuy?'#1e40af':isSell?'#92400e':'#065f46'}}
    .print-btn{display:inline-flex;align-items:center;justify-content:center;padding:10px 20px;background:#0a0a0a;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;margin-top:16px;transition:background 0.2s}
    .print-btn:hover{background:#333}
    @media print{.print-btn{display:none}}
  </style>
</head>
<body>
  <div class="invoice-header">
    <div class="brand">
      <div class="brand-name">APEX<span>Financial</span></div>
      <div class="brand-sub">COMPROBANTE ELECTRÓNICO DE OPERACIÓN</div>
      <div class="brand-sub">Wallbit LLC · Plataforma de Inversión Digital</div>
    </div>
    <div class="invoice-meta">
      <div class="invoice-type">${typeLabel}</div>
      <div class="invoice-id">${txId}</div>
      <div class="invoice-id">${dateStr}</div>
      <button class="print-btn" onclick="window.print()">Imprimir Factura</button>
      ${isSim ? '<br/><div class="demo-badge">⚠ ENTORNO DE SIMULACIÓN — SIN VALOR FISCAL</div>' : ''}
    </div>
  </div>

  <div class="section">
    <div class="section-title">Partes de la Operación</div>
    <div class="info-grid">
      <div class="info-item">
        <label>Titular / Inversor</label>
        <span>${accountName}</span>
      </div>
      <div class="info-item">
        <label>Plataforma</label>
        <span>APEX Financial (Wallbit)</span>
      </div>
      <div class="info-item">
        <label>Tipo de Operación</label>
        <span class="type-badge">${normalized.type}</span>
      </div>
      <div class="info-item">
        <label>Estado</label>
        <span class="status-badge">${normalized.status || 'COMPLETADO'}</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Detalle de la Operación</div>
    <table class="detail-table">
      <thead>
        <tr>
          <th>Descripción</th>
          <th>Activo</th>
          <th>Precio Unit.</th>
          <th>Cantidad</th>
          <th class="right">Importe USD</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>${normalized.desc || typeLabel}</td>
          <td class="mono">${assetDisplay}</td>
          <td class="mono">${isDeposit ? '—' : fmt(price, price < 1 ? 4 : 2)}</td>
          <td class="mono">${isDeposit ? '—' : unitQty.toLocaleString('en-US', { maximumFractionDigits: 6 })}</td>
          <td class="mono right">${fmt(total)}</td>
        </tr>
        ${isTrade && price > 0 && unitQty > 0 ? `
        <tr>
          <td colspan="4" style="font-size:11px;color:#6b7280">Verificación (precio × cantidad)</td>
          <td class="mono right" style="font-size:11px;color:#6b7280">${fmt(price * unitQty)}</td>
        </tr>` : ''}
        <tr>
          <td colspan="4">Comisión (0%)</td>
          <td class="mono right">$0.00</td>
        </tr>
        <tr class="total-row">
          <td colspan="4">TOTAL LIQUIDADO</td>
          <td class="mono right">${fmt(total)}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="footer">
    <p>Este comprobante fue generado automáticamente por APEX AI Copilot el ${new Date().toLocaleString('es-ES')}.</p>
    <p>${isSim ? 'Documento de simulación — sin validez fiscal ni contable.' : 'Operación procesada a través del servicio Wallbit LLC. Sujeto a términos y condiciones.'}</p>
    <p style="margin-top:12px;font-weight:600">APEX Financial · apex-financial.app</p>
  </div>
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 2000);
};
