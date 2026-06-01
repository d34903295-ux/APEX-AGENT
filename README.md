# APEX AI Financial Agent 🚀

APEX Financial es un avanzado asistente de inteligencia artificial y plataforma de simulación diseñado para interactuar con los mercados financieros en tiempo real. 

Utilizando el potente motor de **Claude AI**, APEX actúa como un "Copilot" financiero: escucha tus instrucciones (incluso por voz), analiza el mercado, recomienda estrategias de diversificación, evalúa riesgos y prepara órdenes de compra/venta o depósitos.

## 🎯 ¿Para quién es?
- **Inversores** que buscan un entorno de pruebas (*Paper Trading*) sin riesgo con datos de mercado reales.
- **Traders algorítmicos o manuales** que quieren operar usando comandos de lenguaje natural o mediante la voz.
- **Entusiastas de la tecnología financiera (Fintech)** interesados en la integración de modelos de lenguaje grandes (LLMs) como agentes (Agentic AI) con APIs financieras y herramientas MCP (Model Context Protocol).

## ⚡ Características Principales
- **Inteligencia Artificial Integrada:** Interfaz de chat y terminal (*Intelligence Terminal*) donde el Agente procesa instrucciones naturales ("crea una orden", "analiza el mercado", "¿cuál es el precio de Apple?").
- **Comandos de Voz (Voice Console):** Operaciones manos libres utilizando síntesis y reconocimiento de voz integrado en el navegador.
- **Datos en Tiempo Real:** Integración directa con **Wallbit API** para consultar saldos, balances, activos populares e históricos de transacciones.
- **Modos de Operación:**
  - `Demo`: Interfaz con datos de prueba estáticos para exploraciones iniciales.
  - `Paper Trading`: Simula operaciones reales para medir el rendimiento (PnL) sin dinero real.
  - `Real`: (Si estás conectado a Wallbit y la API Key lo permite).
- **Generación de Comprobantes:** Genera automáticamente facturas y comprobantes electrónicos interactivos (HTML) al finalizar una transacción.
- **Interfaz Moderna y Futurista:** Basada en animaciones de `framer-motion`, estilos SCSS tipo Glassmorphism, monitoreo de precios (Market Pulse) y visualización de red en segundo plano (HUD).

## 🛠️ Tecnologías Utilizadas
- **Core Frontend:** React.js + Vite
- **Estilos / UI:** SCSS, CSS Modules, Framer Motion (para animaciones fluidas)
- **Inteligencia Artificial:** Claude AI API (Anthropic), integrando *Tools* personalizadas (Agent Tools).
- **Conectividad:** Fetch API, MCP (Model Context Protocol), Wallbit API pública, CoinGecko (fallback para criptos), APIs de noticias financieras.
- **Almacenamiento Local:** Persistencia robusta vía `localStorage` para el portafolio en modo *Paper Trading* y el historial del chat.

## 🚀 Cómo Empezar (Desarrollo Local)

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/d34903295-ux/APEX-AGENT.git
   cd APEX-AGENT
   ```

2. **Instala las dependencias:**
   ```bash
   npm install
   ```

3. **Configura tu entorno:**
   (Opcional) Agrega tus claves de Wallbit y Anthropic/Claude en la sección de "Settings" / configuración de la aplicación una vez lanzada, para interactuar de forma real con los modelos.

4. **Inicia el servidor de desarrollo:**
   ```bash
   npm run dev
   ```

5. **Uso:** Abre tu navegador (generalmente en `http://localhost:5173`) y empieza a conversar con tu Agente APEX o utiliza la consola de voz.

---
