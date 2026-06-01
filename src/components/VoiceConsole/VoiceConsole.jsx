// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — VOICE CONSOLE
// Microphone button, waveform, text input, status bar
// ════════════════════════════════════════════════════════════════════

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './VoiceConsole.scss';

const VoiceLED = ({ active }) => {
  // Use more bars for a high-res spectrum analyzer look
  const numBars = 16;
  const baseHeights = Array(numBars).fill(4);
  const [heights, setHeights] = useState(baseHeights);

  useEffect(() => {
    if (!active) {
      setHeights(baseHeights);
      return;
    }
    const interval = setInterval(() => {
      setHeights(heights => heights.map((h, i) => {
        // Create a bell curve effect where center bars are higher
        const distFromCenter = Math.abs(i - numBars / 2) / (numBars / 2);
        const maxH = 32 - (distFromCenter * 16);
        return 4 + Math.random() * maxH;
      }));
    }, 100);
    return () => clearInterval(interval);
  }, [active]);

  return (
    <div className="voice-led" style={{ display: 'flex', gap: '3px', alignItems: 'center', height: '40px' }}>
      {heights.map((h, i) => (
        <motion.div
          key={i}
          animate={{ height: `${h}px` }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          style={{
            width: '4px',
            background: 'linear-gradient(180deg, #00D1FF 0%, #34D399 100%)',
            borderRadius: '2px',
            opacity: active ? 0.8 : 0.2
          }}
        />
      ))}
    </div>
  );
};

const MicButton = ({ isListening, onClick }) => (
  <div className={`mic-btn-wrap ${isListening ? 'mic-btn-wrap--active' : ''}`}>
    {/* Pulse ring */}
    {isListening && <div className="mic-btn-pulse" />}

    {/* Glow halo */}
    <div className={`mic-btn-halo ${isListening ? 'mic-btn-halo--active' : ''}`} />

    {/* Button */}
    <button className="mic-btn" onClick={onClick} aria-label="Toggle voice input">
      {isListening ? (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" x2="12" y1="19" y2="22" />
        </svg>
      ) : (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="2" x2="22" y1="2" y2="22" />
          <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2" />
          <path d="M5 10v2a7 7 0 0 0 12 5.29" />
          <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33" />
          <path d="M9 9v3a3 3 0 0 0 5.12 2.12" />
          <line x1="12" x2="12" y1="19" y2="22" />
        </svg>
      )}
    </button>
  </div>
);

const VoiceConsole = ({ isListening, isSpeaking, currentGuide, interimText, lastError, onToggleMic, onSendText, textInputEnabled }) => {
  const [text, setText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && onSendText) {
      onSendText(text);
      setText('');
    }
  };

  return (
    <div className="voice-console-wrapper">
      <motion.div 
        className="voice-console-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <button 
          className={`voice-console-card__mic ${isListening ? 'active' : ''}`} 
          onClick={onToggleMic}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" x2="12" y1="19" y2="22" />
          </svg>
        </button>

        <div className="voice-console-card__content">
          <p className="voice-console-card__text" style={{ color: lastError ? '#f87171' : (interimText ? '#00D1FF' : undefined) }}>
            {lastError ? lastError : (interimText ? `"${interimText}"` : currentGuide || 'Presiona el micrófono y habla')}
          </p>
          <VoiceLED active={isListening || isSpeaking} />
        </div>
      </motion.div>

      <AnimatePresence>
        {textInputEnabled && (
          <motion.form 
            initial={{ opacity: 0, height: 0, marginTop: 0 }}
            animate={{ opacity: 1, height: 'auto', marginTop: 12 }}
            exit={{ opacity: 0, height: 0, marginTop: 0 }}
            onSubmit={handleSubmit} 
            style={{ width: '100%', display: 'flex', gap: '8px', overflow: 'hidden' }}
          >
            <input 
              type="text" 
              value={text} 
              onChange={e => setText(e.target.value)} 
              placeholder="Escribe un comando para APEX AI..." 
              style={{ flex: 1, padding: '10px 14px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#E8EAF0', fontSize: '12px', fontFamily: "'Fira Code', monospace", outline: 'none' }}
            />
            <button type="submit" style={{ padding: '0 16px', background: 'linear-gradient(135deg, #00D1FF, #1a56db)', border: 'none', borderRadius: '8px', color: '#000', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </motion.form>
        )}
      </AnimatePresence>

      <div className="voice-console-footnote">
        *Habla claro y directo para mejores resultados
      </div>
    </div>
  );
};

export default VoiceConsole;
