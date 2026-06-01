// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — AI SERVICE (OpenRouter / OpenAI compatible)
// Fallback to local WebLLM when no API key is provided
// ════════════════════════════════════════════════════════════════════

import { CreateMLCEngine } from "@mlc-ai/web-llm";

let webLLMEngine = null;
let isInitializingWebLLM = false;

export const buildSystemPrompt = (portfolioData, marketData, mcpContext = {}) => {
  const {
    totalValue = 0, cash = 0, equity = 0, crypto = 0,
    dayChange = 0, dayChangePct = 0, transactions = [],
  } = portfolioData || {};

  const total = totalValue || 1;
  const cashPct    = ((cash / total) * 100).toFixed(1);
  const equityPct  = ((equity / total) * 100).toFixed(1);
  const cryptoPct  = ((crypto / total) * 100).toFixed(1);
  const recentTx   = (transactions || []).slice(0, 3)
    .map(t => `${t.type}: ${t.desc} ($${Math.abs(t.amount).toLocaleString()})`)
    .join('; ') || 'Sin transacciones recientes';

  const btc  = marketData?.find(m => m.symbol === 'BTC/USD' || m.symbol === 'BTC');
  const eth  = marketData?.find(m => m.symbol === 'ETH/USD' || m.symbol === 'ETH');
  const top3 = (marketData || []).slice(0, 5)
    .map(m => `${m.symbol} $${m.price?.toLocaleString()} (${m.change >= 0 ? '+' : ''}${(m.change || 0).toFixed(2)}%)`)
    .join(' | ');

  const mcpLine = mcpContext.transport === 'mcp'
    ? 'Conexión activa vía Wallbit MCP (mcp.wallbit.io) — tools: get_checking_balance, get_stocks_balance, list_transactions, get_asset, create_trade.'
    : 'Conexión vía Wallbit REST API pública.';

  return `Eres APEX A.I., un sistema financiero autónomo impulsado por arquitectura Pipecat y AgenticSeek. 
Operas directamente en la web con ultra-baja latencia y tienes capacidades multimodales de interrupción de voz.

CANAL DE DATOS: ${mcpLine}

ESTADO DEL PORTAFOLIO (TIEMPO REAL):
- Valor total: $${totalValue.toLocaleString()} USD
- USD Efectivo: $${cash.toLocaleString()} USD (${cashPct}%)
- Acciones US: $${equity.toLocaleString()} USD (${equityPct}%)
- Criptomonedas: $${crypto.toLocaleString()} USD (${cryptoPct}%)
- Transacciones recientes: ${recentTx}

MERCADOS GLOBALES:
${top3 || 'No disponibles'}
${btc ? `BTC: $${btc.price?.toLocaleString()} (${btc.change >= 0 ? '+' : ''}${btc.change}%)` : ''}

[SKILLS INYECTADAS Y DIRECTRICES AGÉNTICAS]
1. [Agentic Reasoning]: Piensa paso a paso antes de sugerir trades. Analiza el riesgo, el capital disponible y el contexto del mercado.
2. [Pipecat Voice Flow]: Estás hablando en voz alta con el Director (usuario). Mantén las respuestas extremadamente concisas, sin listas largas ni bloques de código. Habla como un operador experto de Wall Street de élite (directo, táctico, proactivo).
3. [Autonomous Execution]: Usa las herramientas MCP para proponer compras o ventas si el usuario lo pide.
4. [Market Analyst]: Correlaciona noticias implícitas con el precio de BTC o ETH.

REGLAS ESTRICTAS DE RESPUESTA:
1. Responde SIEMPRE en español, máximo 2-3 oraciones.
2. No uses markdown de código ni viñetas largas, ya que esto será sintetizado en audio.
3. Si la orden o pregunta es compleja, usa tu 'AgenticSeek' loop interno para resumir la mejor acción.
4. Si todo está en orden, inicia con ✓. Si hay riesgo, usa ⚠.`;
};

export const sendMessage = async (messages, portfolioData, aiConfig, marketData, mcpContext = {}) => {
  const systemPrompt = buildSystemPrompt(portfolioData, marketData, mcpContext);

  const formattedMessages = [
    { role: 'system', content: systemPrompt },
    ...messages.map(m => ({
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content,
    })),
  ];

  const endpoint = aiConfig?.url || 'https://openrouter.ai/api/v1/chat/completions';
  const model    = aiConfig?.model || 'meta-llama/llama-3.1-8b-instruct:free';
  const key      = aiConfig?.key || '';

  const tools = [
    {
      type: "function",
      function: {
        name: "execute_trade",
        description: "Ejecuta una orden de COMPRA o VENTA de un activo financiero. Usar SOLO cuando el usuario pida explícitamente comprar o vender un activo. Siempre verifica el saldo disponible antes de proceder.",
        parameters: {
          type: "object",
          properties: {
            asset:     { type: "string", description: "Símbolo del activo (ej: BTC, AAPL, TSLA, ETH, NVDA, SOL)" },
            type:      { type: "string", enum: ["COMPRA", "VENTA"], description: "Tipo de orden" },
            amountUsd: { type: "number", description: "Monto en dólares USD a operar (positivo)" }
          },
          required: ["asset", "type", "amountUsd"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "get_asset_price",
        description: "Obtiene el precio actual y variación de un activo desde los mercados en vivo. Usar cuando el usuario pregunte el precio de una acción o crypto antes de decidir si comprar.",
        parameters: {
          type: "object",
          properties: {
            symbol: { type: "string", description: "Símbolo del activo (ej: BTC, AAPL, ETH, TSLA)" }
          },
          required: ["symbol"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "search_financial_news",
        description: "Busca noticias financieras recientes sobre un activo o tema del mercado. Usar para análisis de contexto antes de recomendar trades.",
        parameters: {
          type: "object",
          properties: {
            query: { type: "string", description: "Término de búsqueda (ej: 'Tesla earnings', 'Bitcoin halving', 'Fed interest rates')" }
          },
          required: ["query"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "analyze_portfolio",
        description: "Realiza un análisis profundo del portafolio actual: diversificación, riesgo, activos más rentables, y recomendaciones. Usar cuando el usuario pida analizar su cartera o pedir consejo de inversión.",
        parameters: {
          type: "object",
          properties: {
            focus: { type: "string", enum: ["risk", "performance", "diversification", "recommendations"], description: "Aspecto a analizar" }
          },
          required: ["focus"]
        }
      }
    }
  ];

  const payload = { 
    model, 
    messages: formattedMessages, 
    max_tokens: 512, 
    temperature: 0.7,
    tools,
    tool_choice: "auto"
  };

  if (!key) {
    if (!webLLMEngine) {
      if (isInitializingWebLLM) {
         throw new Error('El motor de IA local (WebLLM) se está inicializando/descargando. Por favor espera un momento y vuelve a intentar...');
      }
      isInitializingWebLLM = true;
      try {
        const initProgressCallback = (initProgress) => {
          console.log("WebLLM Progress:", initProgress.text);
        };
        // Modelo ligero optimizado para la web
        const selectedModel = "Llama-3.2-1B-Instruct-q4f16_1-MLC";
        webLLMEngine = await CreateMLCEngine(selectedModel, {
          initProgressCallback: initProgressCallback,
        });
      } catch (e) {
        isInitializingWebLLM = false;
        throw new Error('No se pudo inicializar WebLLM: ' + e.message + '. (Consejo: Asegúrate de NO estar en modo incógnito, ya que bloquea el guardado en Caché, y de tener espacio disponible en tu navegador).');
      }
      isInitializingWebLLM = false;
    }
    
    try {
      const reply = await webLLMEngine.chat.completions.create({
        messages: formattedMessages,
        temperature: 0.7,
        max_tokens: 512,
        tools: tools,
        tool_choice: "auto"
      });
      const localMessage = reply.choices?.[0]?.message;
      if (!localMessage) throw new Error('La IA local no devolvió contenido en la respuesta.');
      return localMessage;
    } catch (err) {
      throw new Error(`WebLLM Error: ${err.message}`);
    }
  }

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${key}`,
      ...(endpoint.includes('openrouter') ? { 'HTTP-Referer': 'https://apex.financial', 'X-Title': 'APEX Financial' } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`IA API ${res.status}: ${errText.slice(0, 200)}`);
  }

  const data = await res.json();
  const message = data.choices?.[0]?.message;
  if (!message) throw new Error('La IA no devolvió contenido en la respuesta.');
  return message;
};
