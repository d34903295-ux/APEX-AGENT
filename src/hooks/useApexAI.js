// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — AI HOOK
// Conversation with full memory, market context, 20-msg FIFO
// ════════════════════════════════════════════════════════════════════

import { useState, useCallback, useRef } from 'react';
import { sendMessage } from '../services/claude';
import { loadLocalData, saveLocalData } from '../services/wallbit';

const MAX_HISTORY = 20;

const WELCOME_MSG = {
  id: 'welcome',
  role: 'assistant',
  content: '✓ Sistema APEX inicializado. Wallbit MCP conectado — portafolio, trades y transacciones en tiempo real. ¿En qué puedo asistirle, Director?',
  timestamp: new Date().toISOString(),
};

export const useApexAI = (portfolioData, aiConfig, marketData, mcpContext = {}) => {
  const stored = loadLocalData('chat_history');
  const [messages, setMessages] = useState(
    stored && stored.length > 0 ? stored : [WELCOME_MSG]
  );
  const [isTyping, setIsTyping] = useState(false);

  // ─── AGENT TOOL HANDLERS ────────────────────────────────────────
  // These run locally when the AI calls a tool
  const handleGetAssetPrice = useCallback((symbol, marketData) => {
    const upper = symbol.toUpperCase();
    const item = (marketData || []).find(m => m.symbol === upper || m.symbol === `${upper}/USD`);
    if (item) {
      return `${upper}: $${Number(item.price).toLocaleString('en-US', { minimumFractionDigits: 2 })} USD (${item.change >= 0 ? '+' : ''}${Number(item.change).toFixed(2)}% hoy). Fuente: mercado en vivo.`;
    }
    return `No se encontró precio en tiempo real para ${upper}. El activo puede no estar disponible en el feed actual.`;
  }, []);

  const handleSearchNews = useCallback(async (query) => {
    try {
      // Use GNews public RSS (no key needed for RSS format)
      const encoded = encodeURIComponent(`${query} finance stock market`);
      const url = `https://gnews.io/api/v4/search?q=${encoded}&lang=en&max=5&apikey=free`;
      // Fallback: DuckDuckGo Instant Answer API
      const ddgUrl = `https://api.duckduckgo.com/?q=${encodeURIComponent(query + ' financial news 2025')}&format=json&no_html=1&skip_disambig=1`;
      const res = await fetch(ddgUrl, { signal: AbortSignal.timeout(5000) });
      const data = await res.json();

      const abstract = data.AbstractText ? data.AbstractText.slice(0, 300) : null;
      const related = (data.RelatedTopics || [])
        .filter(t => t.Text)
        .slice(0, 3)
        .map(t => `• ${t.Text.slice(0, 120)}`)
        .join('\n');

      if (abstract || related) {
        return `Noticias sobre "${query}":\n${abstract ? abstract + '\n' : ''}${related}`;
      }
      return `No se encontraron noticias inmediatas sobre "${query}". Considera buscar en Bloomberg o Reuters para contexto actualizado.`;
    } catch {
      return `No se pudo acceder a noticias en este momento. Contexto de mercado: el agente recomienda verificar noticias recientes antes de ejecutar operaciones significativas.`;
    }
  }, []);

  const handleAnalyzePortfolio = useCallback((focus, portfolioData, marketData) => {
    const { totalValue = 0, cash = 0, equity = 0, crypto = 0, transactions = [] } = portfolioData || {};
    const total = totalValue || 1;

    if (focus === 'risk') {
      const cryptoPct = ((crypto / total) * 100).toFixed(1);
      const equityPct = ((equity / total) * 100).toFixed(1);
      const cashPct   = ((cash / total) * 100).toFixed(1);
      const risk = cryptoPct > 60 ? 'ALTO' : cryptoPct > 30 ? 'MODERADO' : 'BAJO';
      return `Análisis de Riesgo:\n- Riesgo general: ${risk}\n- Crypto: ${cryptoPct}% | Acciones: ${equityPct}% | Cash: ${cashPct}%\n- ${cryptoPct > 50 ? '⚠ Alta exposición a crypto — considera diversificar.' : '✓ Exposición balanceada.'}`;
    }
    if (focus === 'diversification') {
      const assets = (marketData || []).slice(0, 5).map(m => m.symbol).join(', ');
      return `Diversificación del portafolio:\n- Sectores: Crypto ${((crypto/total)*100).toFixed(0)}% | Equity ${((equity/total)*100).toFixed(0)}% | Cash ${((cash/total)*100).toFixed(0)}%\n- Activos disponibles en mercado: ${assets}\n- Recomendación: mantener cash entre 15-25% para oportunidades.`;
    }
    if (focus === 'performance') {
      const recentTxs = (transactions || []).slice(0, 5).map(t => `${t.type} ${t.asset || ''}: ${t.amount >= 0 ? '+' : ''}$${Math.abs(t.amount || 0).toLocaleString()}`).join('\n');
      return `Performance reciente:\n- Valor total: $${totalValue.toLocaleString()}\n- Últimas operaciones:\n${recentTxs || 'Sin operaciones registradas.'}`;
    }
    if (focus === 'recommendations') {
      const lowCash = cash < totalValue * 0.1;
      const highCrypto = crypto > totalValue * 0.6;
      const recs = [];
      if (lowCash) recs.push('⚠ Liquidez baja — considera aumentar posición en USD.');
      if (highCrypto) recs.push('⚠ Alta concentración en crypto — diversifica en acciones.');
      if (!lowCash && !highCrypto) recs.push('✓ Portafolio saludable. Evalúa incrementar exposición en tech (NVDA, AAPL) dado el contexto de IA.');
      return `Recomendaciones APEX:\n${recs.join('\n')}`;
    }
    return 'Análisis no disponible.';
  }, []);

  // ─── PROCESS MESSAGE ────────────────────────────────────────────
  const processMessage = useCallback(async (userText, onToolCall) => {
    if (!userText?.trim()) return null;

    const userMsg = {
      id: `u_${Date.now()}`,
      role: 'user',
      content: userText.trim(),
      timestamp: new Date().toISOString(),
    };

    let currentMessages;
    setMessages(prev => {
      currentMessages = [...prev, userMsg];
      return currentMessages;
    });
    setIsTyping(true);

    try {
      const forAPI = (currentMessages || [messages, userMsg].flat())
        .filter(m => m.id !== 'welcome')
        .map(m => ({ role: m.role, content: m.content }))
        .slice(-MAX_HISTORY);

      const response = await sendMessage(forAPI, portfolioData, aiConfig, marketData, mcpContext);
      let replyContent = '';

      // ── Handle tool calls ──────────────────────────────────────
      if (response.tool_calls && response.tool_calls.length > 0) {
        const toolCall = response.tool_calls[0];
        const toolName = toolCall.function.name;
        let toolResult = '';

        try {
          const args = JSON.parse(toolCall.function.arguments);

          if (toolName === 'execute_trade') {
            if (onToolCall) onToolCall(args);
            replyContent = `📋 Preparando orden: ${args.type} $${args.amountUsd?.toLocaleString()} USD de ${args.asset}. El modal de confirmación está abierto — confirma para ejecutar.`;
            toolResult = 'order_prepared';

          } else if (toolName === 'get_asset_price') {
            toolResult = handleGetAssetPrice(args.symbol, marketData);
            replyContent = toolResult;

          } else if (toolName === 'search_financial_news') {
            toolResult = await handleSearchNews(args.query);
            replyContent = toolResult;

          } else if (toolName === 'analyze_portfolio') {
            toolResult = handleAnalyzePortfolio(args.focus, portfolioData, marketData);
            replyContent = toolResult;

          } else {
            replyContent = `Herramienta "${toolName}" no implementada aún.`;
          }
        } catch (parseErr) {
          replyContent = `⚠ Error procesando la herramienta: ${parseErr.message}`;
        }

        // Send tool result back to the model for a natural-language summary
        if (toolResult && toolName !== 'execute_trade') {
          try {
            const followUp = await sendMessage(
              [
                ...forAPI,
                { role: 'assistant', content: null, tool_calls: response.tool_calls },
                { role: 'tool', tool_call_id: toolCall.id, content: String(toolResult) }
              ],
              portfolioData, aiConfig, marketData, mcpContext
            );
            if (followUp.content) replyContent = followUp.content;
          } catch {
            // keep toolResult as replyContent if follow-up fails
          }
        }

      } else {
        replyContent = response.content || '⚠ Sin respuesta del módulo de inteligencia.';
      }

      const aiMsg = {
        id: `ai_${Date.now()}`,
        role: 'assistant',
        content: replyContent,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => {
        const updated = [...prev, aiMsg].slice(-MAX_HISTORY - 1);
        saveLocalData('chat_history', updated.slice(-10));
        return updated;
      });

      // ─── TEXT TO SPEECH ──────────────────────────────────────
      if (window.speechSynthesis && replyContent) {
        window.speechSynthesis.cancel();
        const cleanText = replyContent
          .replace(/[\u{1F600}-\u{1F6FF}\u{1F300}-\u{1F5FF}\u{1F900}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
          .replace(/\*+/g, '').replace(/✓/g, '').replace(/⚠/g, '')
          .replace(/📋/g, '').replace(/\[PAPER\]/g, 'paper').trim();
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'es-ES'; utterance.rate = 1.05; utterance.pitch = 0.9;
        const voices = window.speechSynthesis.getVoices();
        const esVoice = voices.find(v => v.lang.startsWith('es') && (v.name.includes('Google') || v.name.includes('Sabina') || v.name.includes('Pablo')));
        if (esVoice) utterance.voice = esVoice;
        window.speechSynthesis.speak(utterance);
      }

      setIsTyping(false);
      return replyContent;
    } catch (err) {
      const errMsg = {
        id: `e_${Date.now()}`,
        role: 'assistant',
        content: `⚠ ${err.message || 'Error de comunicación. Verifique su API Key en Configuración.'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
      setIsTyping(false);
      return null;
    }
  }, [portfolioData, aiConfig, marketData, mcpContext, handleGetAssetPrice, handleSearchNews, handleAnalyzePortfolio]);

  // ─── CLEAR CONVERSATION ─────────────────────────────────────────
  const clearConversation = useCallback(() => {
    setMessages([{ ...WELCOME_MSG, id: 'welcome_' + Date.now() }]);
    saveLocalData('chat_history', []);
  }, []);

  return { messages, isTyping, processMessage, clearConversation };
};
