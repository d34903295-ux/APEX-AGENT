// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — INTELLIGENCE TERMINAL
// Real-time AI chat with Claude API + typewriter effect
// ════════════════════════════════════════════════════════════════════

import React, { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './IntelligenceTerminal.scss';

const TypingDots = () => (
  <div className="typing-dots">
    <span style={{ animationDelay: '0ms' }} />
    <span style={{ animationDelay: '150ms' }} />
    <span style={{ animationDelay: '300ms' }} />
  </div>
);

const TypewriterText = ({ text }) => {
  const safeText = text == null ? '' : String(text);
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed('');
    setDone(false);
    let i = 0;
    const interval = setInterval(() => {
      if (i < safeText.length) {
        setDisplayed(safeText.slice(0, i + 1));
        i++;
      } else {
        setDone(true);
        clearInterval(interval);
      }
    }, 25);
    return () => clearInterval(interval);
  }, [safeText]);

  return (
    <span>
      {displayed}
      {!done && <span className="terminal-cursor">▌</span>}
    </span>
  );
};

const IntelligenceTerminal = ({ messages = [], isTyping, latestId, aiConfig, mcpStatus }) => {
  const scrollRef = useRef(null);
  const safeMessages = Array.isArray(messages) ? messages : [];

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [safeMessages, isTyping]);

  return (
    <motion.div
      className="intel-terminal"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
    >
      <div className="hud-section-header">
        <span>APEX INTELLIGENCE TERMINAL</span>
        <span className="intel-terminal__badge">
          {aiConfig?.model?.split('/').pop() || 'APEX AI'}{' '}
          <span className="text-emerald">ONLINE</span>
          {mcpStatus === 'connected' && <span className="text-cyan"> · MCP</span>}
        </span>
      </div>

      <div className="intel-terminal__chat" ref={scrollRef}>
        <AnimatePresence initial={false}>
          {safeMessages.map((msg, i) => {
            const isAI = msg.role === 'assistant';
            const isLatest = msg.id === latestId && isAI;

            return (
              <motion.div
                key={msg.id}
                className={`intel-bubble ${isAI ? 'intel-bubble--ai' : 'intel-bubble--user'}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.05 }}
              >
                <div className="intel-bubble__label">
                  {isAI ? 'APEX A.I.' : 'TÚ'}
                </div>
                <div className="intel-bubble__content">
                  {isLatest ? <TypewriterText text={msg.content} /> : msg.content}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Typing indicator */}
        {isTyping && (
          <motion.div
            className="intel-bubble intel-bubble--ai"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="intel-bubble__label">APEX A.I.</div>
            <div className="intel-bubble__content">
              <TypingDots />
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

export default IntelligenceTerminal;
