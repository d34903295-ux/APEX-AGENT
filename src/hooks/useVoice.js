import { useState, useEffect, useRef, useCallback } from 'react';

export function useVoice({ onTranscript, lang = 'es-ES', continuous = false }) {
  const [isListening, setIsListening]   = useState(false);
  const [isSpeaking, setIsSpeaking]     = useState(false);
  const [isSupported, setIsSupported]   = useState(false);
  const [micGranted, setMicGranted]     = useState(false);
  const recognitionRef = useRef(null);
  const synthRef       = useRef(window.speechSynthesis);
  const restartRef     = useRef(false);
  const [lastError, setLastError]       = useState(null);

  const onTranscriptRef = useRef(onTranscript);
  useEffect(() => { onTranscriptRef.current = onTranscript; }, [onTranscript]);

  // ─── Build SpeechRecognition once ──────────────────────────────────
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { setIsSupported(false); return; }

    setIsSupported(true);
    const recognition = new SpeechRecognition();
    recognition.lang            = lang;
    recognition.continuous      = false;
    recognition.interimResults  = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setLastError(null);
      setIsListening(true);
      window.speechSynthesis?.cancel(); // Pipecat-style interrupt
    };

    recognition.onend = () => {
      setIsListening(false);
      // Restart if continuous listening is enabled and no error occurred
      if (restartRef.current && !lastError) {
        try { recognition.start(); } catch(e) {}
      }
    };

    recognition.onerror = (e) => {
      console.warn('Microphone/Speech error:', e.error);
      setLastError(`Error: ${e.error}`);
      setIsListening(false);
      restartRef.current = false;
    };

    recognition.onresult = (event) => {
      window.speechSynthesis?.cancel();
      const transcript = event.results[0][0].transcript.trim();
      if (transcript.length > 0 && onTranscriptRef.current) {
        onTranscriptRef.current(transcript);
      }
    };

    recognitionRef.current = recognition;
    return () => {
      restartRef.current = false;
      try { recognition.stop(); } catch(e) {}
    };
  }, [lang]);

  // ─── Start listening ────────────
  const startListening = useCallback(() => {
    if (!recognitionRef.current || isListening) return;
    restartRef.current = false;
    try {
      recognitionRef.current.start();
    } catch(e) {
      console.warn('Could not start recognition:', e);
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    restartRef.current = false;
    try { recognitionRef.current?.stop(); } catch(e) {}
    setIsListening(false);
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) stopListening();
    else startListening();
  }, [isListening, startListening, stopListening]);

  // ─── Text-to-Speech ───────────────────────────────────────────────
  const [availableVoices, setAvailableVoices] = useState([]);
  const [selectedVoiceURI, setSelectedVoiceURI] = useState(null);

  // Cargar voces disponibles
  useEffect(() => {
    const loadVoices = () => {
      if (!synthRef.current) return;
      const voices = synthRef.current.getVoices();
      // Filtrar voces en español, o dejar todas si no hay en español
      let esVoices = voices.filter(v => v.lang.startsWith('es'));
      if (esVoices.length === 0) esVoices = voices; // fallback

      setAvailableVoices(esVoices);
      
      // Auto-seleccionar una por defecto si no hay ninguna seleccionada
      if (esVoices.length > 0 && !selectedVoiceURI) {
        const defaultVoice = esVoices.find(v => v.name.includes('Google') || v.name.includes('Sabina')) || esVoices[0];
        setSelectedVoiceURI(defaultVoice.voiceURI);
      }
    };

    if (synthRef.current?.getVoices().length > 0) loadVoices();
    else synthRef.current?.addEventListener('voiceschanged', loadVoices);

    return () => synthRef.current?.removeEventListener('voiceschanged', loadVoices);
  }, [selectedVoiceURI]);

  const speak = useCallback((text) => {
    if (!synthRef.current) return;
    synthRef.current.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang  = lang;
    utterance.rate  = 1.05;
    utterance.pitch = 0.9;

    const voices = synthRef.current.getVoices();
    if (selectedVoiceURI) {
      const chosenVoice = voices.find(v => v.voiceURI === selectedVoiceURI);
      if (chosenVoice) utterance.voice = chosenVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend   = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    synthRef.current.speak(utterance);
  }, [lang, selectedVoiceURI]);

  const cancelSpeech = useCallback(() => {
    synthRef.current?.cancel();
    setIsSpeaking(false);
  }, []);

  return {
    isListening, isSpeaking, isSupported, micGranted, lastError,
    startListening, stopListening, toggleListening,
    speak, cancelSpeech,
    availableVoices, selectedVoiceURI, setSelectedVoiceURI
  };
}
