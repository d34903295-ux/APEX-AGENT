// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — TRANSACTION MODAL
// Real Wallbit trades + internal operations
// ════════════════════════════════════════════════════════════════════

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchTradableAssets } from '../../services/wallbit';
import { toSimModalType, presetAssetSymbol, isBuyType } from '../../utils/paperPortfolio';
import './SimModal.scss';

const TX_TYPES = [
  { value: 'DEPÓSITO', label: '+ A INVERSIÓN', color: 'emerald', hint: 'DEFAULT → INVESTMENT' },
  { value: 'COMPRA',   label: '▲ COMPRA',      color: 'cyan',    hint: 'Trade MARKET BUY' },
  { value: 'VENTA',    label: '▼ VENTA',       color: 'gold',    hint: 'Trade MARKET SELL' },
  { value: 'RETIRO',   label: '– A CHECKING',  color: 'rose',    hint: 'INVESTMENT → DEFAULT' },
];

const SimModal = ({
  isOpen, onClose, onConfirm, preselectedAsset, preselectedType, preselectedAmount,
  apiKey, marketData, isLoading, error, dataMode = 'real', spendableCash = 0,
}) => {
  const isSimMode = dataMode === 'demo' || dataMode === 'paper';
  const [type, setType]     = useState(toSimModalType(preselectedType) || 'COMPRA');
  const [asset, setAsset]   = useState(presetAssetSymbol(preselectedAsset) || '');
  const [amount, setAmount] = useState('');
  const [units, setUnits]   = useState('');
  const [desc, setDesc]     = useState('');
  const [assets, setAssets] = useState([]);

  useEffect(() => {
    if (!isOpen || !apiKey) return;
    fetchTradableAssets(apiKey).then(setAssets).catch(() => {
      setAssets((marketData || []).filter(m => !m.symbol.includes('/')).map(m => ({
        symbol: m.symbol.replace('/USD', ''),
        name: m.name,
        price: m.price,
        type: 'equity',
      })));
    });
  }, [isOpen, apiKey, marketData]);

  useEffect(() => {
    if (!isOpen) return;
    if (preselectedType) setType(toSimModalType(preselectedType));
    const sym = presetAssetSymbol(preselectedAsset);
    if (sym) setAsset(sym);
    if (preselectedAmount) setAmount(String(preselectedAmount));
    else setAmount('');
    setUnits('');
  }, [preselectedType, preselectedAsset, preselectedAmount, isOpen]);

  const needsAsset = type === 'COMPRA' || type === 'VENTA';
  const selectedAsset = assets.find(a => a.symbol === asset);

  const calcUnits = (amt) => {
    if (!selectedAsset?.price || !amt) return '';
    return (parseFloat(amt) / selectedAsset.price).toFixed(6);
  };
  const calcAmount = (u) => {
    if (!selectedAsset?.price || !u) return '';
    return (parseFloat(u) * selectedAsset.price).toFixed(2);
  };

  const handleAmountChange = (v) => {
    setAmount(v);
    if (needsAsset && selectedAsset) setUnits(calcUnits(v));
  };
  const handleUnitsChange = (v) => {
    setUnits(v);
    if (needsAsset && selectedAsset) setAmount(calcAmount(v));
  };
  const handleAssetChange = (sym) => {
    setAsset(sym);
    const a = assets.find(x => x.symbol === sym);
    if (a && units) setAmount((parseFloat(units) * a.price).toFixed(2));
  };

  const handleConfirm = () => {
    const amt = parseFloat(amount);
    if (!amount || isNaN(amt) || amt <= 0) return;

    if (isBuyType(type) && spendableCash > 0 && amt > spendableCash) {
      return;
    }

    const colorMap = { DEPÓSITO: 'emerald', COMPRA: 'cyan', VENTA: 'gold', RETIRO: 'rose' };
    const txAmount = (type === 'RETIRO' || type === 'COMPRA') ? -amt : amt;

    const autoDesc = needsAsset && selectedAsset
      ? `${type} ${units || ''} ${asset} @ $${selectedAsset.price?.toLocaleString()}`
      : desc.trim() || type;

    const unitPrice = needsAsset ? (parseFloat(selectedAsset?.price) || 0) : 0;
    const qty = needsAsset
      ? (parseFloat(units) || (unitPrice > 0 ? amt / unitPrice : 0))
      : undefined;

    onConfirm({
      type,
      desc: desc.trim() || autoDesc,
      amount: txAmount,
      amountUsd: amt,
      color: colorMap[type],
      asset: needsAsset ? asset : undefined,
      assetName: selectedAsset?.name,
      price: unitPrice,
      units: qty,
      total: amt,
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div className="sim-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }} onClick={onClose}>
          <motion.div className="sim-modal" initial={{ opacity: 0, scale: 0.92, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.92, y: 30 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }} onClick={e => e.stopPropagation()}>

            <div className="sim-modal__header">
              <h2 className="sim-modal__title">NUEVA OPERACIÓN</h2>
              <button className="sim-modal__close" onClick={onClose} aria-label="Cerrar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/>
                </svg>
              </button>
            </div>

            {error && (
              <div className="sim-modal__error" style={{ color: '#f87171', fontSize: 11, padding: '0 16px 8px' }}>
                ⚠ {error}
              </div>
            )}

            {(isSimMode || spendableCash > 0) && (
              <div style={{
                margin: '0 16px 12px', padding: '10px 12px', borderRadius: 8,
                background: dataMode === 'demo' ? 'rgba(251,191,36,0.08)' : dataMode === 'paper' ? 'rgba(0,209,255,0.08)' : 'rgba(52,211,153,0.06)',
                border: `1px solid ${dataMode === 'demo' ? 'rgba(251,191,36,0.25)' : dataMode === 'paper' ? 'rgba(0,209,255,0.25)' : 'rgba(52,211,153,0.2)'}`,
                fontSize: 11, fontFamily: "'Fira Code', monospace",
              }}>
                <span style={{ color: '#8A8F98' }}>Saldo disponible para operar: </span>
                <strong style={{ color: dataMode === 'demo' ? '#FBBF24' : dataMode === 'paper' ? '#00D1FF' : '#34D399' }}>
                  ${(Number(spendableCash) || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })} USD
                </strong>
                <span style={{ color: '#8A8F98' }}>
                  {dataMode === 'demo' ? ' (Demo)' : dataMode === 'paper' ? ' (Paper)' : ' (Wallbit real)'}
                </span>
              </div>
            )}

            <div className="sim-modal__field">
              <label className="sim-modal__label">TIPO DE OPERACIÓN (WALLBIT API)</label>
              <div className="sim-modal__types">
                {TX_TYPES.map(t => (
                  <button key={t.value} id={`tx-type-${t.value.toLowerCase()}`}
                    className={`sim-modal__type-btn sim-modal__type-btn--${t.color} ${type === t.value ? 'sim-modal__type-btn--active' : ''}`}
                    onClick={() => { setType(t.value); if (t.value !== 'COMPRA' && t.value !== 'VENTA') setAsset(''); }}>
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {needsAsset && (
              <div className="sim-modal__field">
                <label className="sim-modal__label">ACTIVO (precio en vivo)</label>
                <div className="sim-modal__asset-grid">
                  {assets.length === 0 ? (
                    <p style={{ fontSize: 11, color: '#8A8F98' }}>Cargando activos de Wallbit...</p>
                  ) : assets.map(a => (
                    <button key={a.symbol}
                      className={`sim-modal__asset-btn ${asset === a.symbol ? 'sim-modal__asset-btn--active' : ''} sim-modal__asset-btn--${a.type}`}
                      onClick={() => handleAssetChange(a.symbol)}>
                      <span className="sim-asset-symbol">{a.symbol}</span>
                      <span className="sim-asset-price">${(Number(a.price) || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="sim-modal__row">
              <div className="sim-modal__field">
                <label className="sim-modal__label">MONTO (USD)</label>
                <input type="number" value={amount} onChange={e => handleAmountChange(e.target.value)}
                  placeholder="10,000.00" className="sim-modal__input" id="sim-amount" min="0" step="0.01" />
              </div>
              {needsAsset && (
                <div className="sim-modal__field">
                  <label className="sim-modal__label">CANTIDAD ({asset || '—'})</label>
                  <input type="number" value={units} onChange={e => handleUnitsChange(e.target.value)}
                    placeholder="0.00" className="sim-modal__input" id="sim-units" min="0" step="any" />
                </div>
              )}
            </div>

            {amount && parseFloat(amount) > 0 && (
              <div className="sim-modal__preview">
                {type === 'COMPRA' && asset && (
                  <span>
                    Comprarás {units} {asset} por ${(parseFloat(amount) || 0).toLocaleString()} USD
                    {spendableCash > 0 && (
                      <> — saldo restante: ${(Math.max(0, spendableCash - parseFloat(amount)) || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</>
                    )}
                  </span>
                )}
                {type === 'VENTA' && asset && <span>Venderás {units} {asset} y recibirás ${(parseFloat(amount) || 0).toLocaleString()} USD</span>}
                {type === 'DEPÓSITO' && <span>Transferirás ${(parseFloat(amount) || 0).toLocaleString()} USD a cuenta de inversión</span>}
                {type === 'RETIRO' && <span>Transferirás ${(parseFloat(amount) || 0).toLocaleString()} USD a cuenta checking</span>}
              </div>
            )}

            {isBuyType && isBuyType(type) && amount && parseFloat(amount) > spendableCash && spendableCash > 0 && (
              <div style={{ color: '#f87171', fontSize: 11, padding: '0 16px 8px' }}>
                ⚠ Monto superior al saldo disponible (${(Number(spendableCash) || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })})
              </div>
            )}

            <div className="sim-modal__field">
              <label className="sim-modal__label">DESCRIPCIÓN (opcional)</label>
              <input type="text" value={desc} onChange={e => setDesc(e.target.value)}
                placeholder="Ej: Wire Transfer, Venta parcial..." className="sim-modal__input" id="sim-description"
                onKeyDown={e => e.key === 'Enter' && !isLoading && handleConfirm()} />
            </div>

            <button className="sim-modal__confirm" id="sim-confirm-btn"
              onClick={handleConfirm}
              disabled={
                isLoading || !amount || parseFloat(amount) <= 0 || (needsAsset && !asset)
                || (isBuyType(type) && spendableCash > 0 && parseFloat(amount) > spendableCash)
              }>
              {isLoading ? 'EJECUTANDO...' : (isSimMode || spendableCash > 0) ? 'CONFIRMAR (SIMULADO)' : 'CONFIRMAR EN WALLBIT'}
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SimModal;
