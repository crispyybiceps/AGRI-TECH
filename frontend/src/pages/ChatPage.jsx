import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  IoArrowBack,
  IoSend,
  IoMic,
  IoMicOff,
  IoVolumeHighOutline,
  IoStopCircleOutline,
  IoFlagOutline,
  IoCheckmarkCircle,
  IoCallOutline,
  IoInformationCircleOutline,
} from 'react-icons/io5';
import api from '../api/axios';

export default function ChatPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState(null);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang =
        i18n.language === 'mr'
          ? 'mr-IN'
          : i18n.language === 'hi'
          ? 'hi-IN'
          : 'en-IN';

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputMessage((prev) => (prev ? `${prev} ${transcript}` : transcript));
        setIsListening(false);
      };

      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);

      recognitionRef.current = recognition;
    }
  }, [i18n.language]);

  // Load farms & set initial message
  useEffect(() => {
    const fetchFarms = async () => {
      try {
        const res = await api.get('/farms');
        setFarms(res.data);
        if (res.data.length > 0) {
          setSelectedFarmId(res.data[0].id);
        }
      } catch (err) {
        console.error('Failed to load farms', err);
      }
    };
    fetchFarms();

    // Initial greeting
    const greeting =
      i18n.language === 'mr'
        ? 'नमस्कार शेतकरी बंधूंनो! मी आपला ॲग्रीटेक कृषी सल्लागार आहे. आज मी आपल्याला काय मदत करू शकेन?'
        : i18n.language === 'hi'
        ? 'नमस्ते किसान भाई! मैं आपका एग्रीटेक कृषि सलाहकार हूं। आज मैं आपकी क्या सहायता कर सकता हूं?'
        : 'Hello! I am your AgriTech agricultural assistant. How can I help you with your crops today?';

    setMessages([
      {
        id: 'init',
        sender: 'assistant',
        content: greeting,
        sources: ['cibrc_pesticides_and_ipm.md', 'crop_selection_maharashtra.md'],
        created_at: new Date().toISOString(),
      },
    ]);
  }, [i18n.language]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Voice recognition toggle
  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.lang =
        i18n.language === 'mr'
          ? 'mr-IN'
          : i18n.language === 'hi'
          ? 'hi-IN'
          : 'en-IN';
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  // Text-To-Speech for assistant responses
  const handleSpeak = (msgId, text) => {
    if (!synthRef.current) return;

    if (speakingMsgId === msgId) {
      synthRef.current.cancel();
      setSpeakingMsgId(null);
      return;
    }

    synthRef.current.cancel();
    const cleanText = text.replace(/[*#_`]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang =
      i18n.language === 'mr'
        ? 'mr-IN'
        : i18n.language === 'hi'
        ? 'hi-IN'
        : 'en-US';
    utterance.rate = 0.9;

    utterance.onend = () => setSpeakingMsgId(null);
    utterance.onerror = () => setSpeakingMsgId(null);

    synthRef.current.speak(utterance);
    setSpeakingMsgId(msgId);
  };

  // Send message
  const handleSendMessage = async (textToSend) => {
    const text = textToSend || inputMessage;
    if (!text.trim() || loading) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      content: text.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      const res = await api.post('/chat', {
        message: text.trim(),
        session_id: sessionId,
        farm_id: selectedFarmId,
        language: i18n.language,
      });

      setSessionId(res.data.session_id);

      const asstMsg = {
        id: res.data.message_id,
        sender: 'assistant',
        content: res.data.reply,
        sources: res.data.sources || [],
        tools_used: res.data.tools_used || [],
        is_fallback: res.data.is_fallback,
        mode_badge: res.data.mode_badge,
        created_at: res.data.created_at,
      };

      setMessages((prev) => [...prev, asstMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'assistant',
          content: '⚠️ Failed to connect to AgriTech Expert. Please try again.',
          sources: [],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Flag message for expert review
  const handleFlagMessage = async (msgId) => {
    try {
      await api.post(`/chat/messages/${msgId}/flag`, {
        reason: 'Farmer requested expert review for verification',
      });
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, is_flagged: true } : m))
      );
      alert(t('chat.flagged'));
    } catch (err) {
      alert('Flagging failed.');
    }
  };

  const quickPrompts = [
    t('chat.quickPrompt1'),
    t('chat.quickPrompt2'),
    t('chat.quickPrompt3'),
  ];

  return (
    <div className="app-container flex flex-col h-screen bg-gray-50 pb-20">
      {/* Top Header */}
      <header className="px-4 py-3 bg-white border-b border-gray-200 flex items-center justify-between shadow-xs z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="p-1.5 text-gray-700 hover:bg-gray-100 rounded-lg"
            aria-label={t('common.back')}
          >
            <IoArrowBack className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-gray-900 leading-tight">
              🌾 {t('chat.title')}
            </h1>
            <p className="text-xs text-green-700 font-semibold">
              ● Online • CIB&RC Certified
            </p>
          </div>
        </div>

        {/* Talk to Expert button */}
        <button
          onClick={() => navigate('/soil')}
          className="flex items-center gap-1 bg-amber-100 text-amber-900 text-xs font-bold px-2.5 py-1.5 rounded-xl border border-amber-300 shadow-xs"
        >
          <IoCallOutline className="w-3.5 h-3.5" />
          <span>KVK</span>
        </button>
      </header>

      {/* Farm Context Selector */}
      {farms.length > 0 && (
        <div className="px-4 py-1.5 bg-green-50 border-b border-green-200 flex items-center justify-between text-xs font-semibold text-green-900">
          <span className="flex items-center gap-1">
            📍 {t('chat.selectFarm')}:
          </span>
          <select
            value={selectedFarmId || ''}
            onChange={(e) => setSelectedFarmId(Number(e.target.value))}
            className="bg-transparent border-0 font-bold text-green-950 py-0 pr-6 text-xs focus:ring-0"
          >
            {farms.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.name} ({farm.crops || 'No crops'})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3.5">
        {messages.map((m) => {
          const isUser = m.sender === 'user';
          return (
            <div
              key={m.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl p-3.5 text-sm shadow-sm ${
                  isUser
                    ? 'bg-green-600 text-white rounded-br-none'
                    : 'bg-white text-gray-900 border border-gray-200 rounded-bl-none'
                }`}
              >
                <p className="whitespace-pre-line leading-relaxed font-medium">
                  {m.content}
                </p>

                {/* AI / Fallback mode badge */}
                {!isUser && m.mode_badge && (
                  <div className="mt-1.5 flex items-center">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                      m.is_fallback
                        ? 'bg-amber-100 text-amber-900 border border-amber-300'
                        : 'bg-green-100 text-green-900 border border-green-300'
                    }`}>
                      {m.mode_badge}
                    </span>
                  </div>
                )}

                {/* Sources & Action bar on Assistant messages */}
                {!isUser && (
                  <div className="mt-2.5 pt-2 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleSpeak(m.id, m.content)}
                        className="flex items-center gap-1 text-green-700 font-semibold hover:text-green-800"
                        aria-label={t('chat.readAloud')}
                      >
                        {speakingMsgId === m.id ? (
                          <>
                            <IoStopCircleOutline className="w-4 h-4 text-red-600" />
                            <span className="text-red-600">{t('chat.stop')}</span>
                          </>
                        ) : (
                          <>
                            <IoVolumeHighOutline className="w-4 h-4" />
                            <span>{t('chat.readAloud')}</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => handleFlagMessage(m.id)}
                        disabled={m.is_flagged}
                        className={`flex items-center gap-0.5 ml-2 ${
                          m.is_flagged
                            ? 'text-gray-400 cursor-not-allowed'
                            : 'text-gray-400 hover:text-red-600'
                        }`}
                        title={t('chat.flag')}
                      >
                        <IoFlagOutline className="w-3.5 h-3.5" />
                        <span>{m.is_flagged ? t('chat.flagged') : t('chat.flag')}</span>
                      </button>
                    </div>

                    <span className="text-[10px] text-gray-400">
                      {new Date(m.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                )}

                {/* Citations Tag */}
                {!isUser && m.sources && m.sources.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {m.sources.map((s, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-mono"
                      >
                        📚 {s.replace('.md', '')}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Loading Spinner Indicator */}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-gray-500 bg-white p-2.5 rounded-xl w-32 border shadow-xs">
            <div className="w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full animate-spin" />
            <span>Typing...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompt Chips */}
      <div className="px-4 py-1.5 flex gap-2 overflow-x-auto no-scrollbar bg-gray-100">
        {quickPrompts.map((prompt, i) => (
          <button
            key={i}
            onClick={() => handleSendMessage(prompt)}
            className="flex-shrink-0 bg-white border border-gray-300 text-xs text-gray-700 font-semibold px-3 py-1.5 rounded-full shadow-xs hover:bg-gray-50 active:scale-95"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <div className="p-3 bg-white border-t border-gray-200">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          {/* Big Voice Microphone Button */}
          <button
            type="button"
            onClick={toggleListening}
            className={`p-3 rounded-full shadow-md transition-all ${
              isListening
                ? 'bg-red-600 text-white animate-pulse'
                : 'bg-green-100 text-green-800 hover:bg-green-200 active:scale-95'
            }`}
            aria-label={t('chat.voiceSearch')}
          >
            {isListening ? (
              <IoMicOff className="w-6 h-6" />
            ) : (
              <IoMic className="w-6 h-6" />
            )}
          </button>

          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={
              isListening ? t('chat.listening') : t('chat.placeholder')
            }
            className="flex-1 text-sm py-2.5 px-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500"
          />

          <button
            type="submit"
            disabled={!inputMessage.trim() || loading}
            className="p-3 bg-green-600 text-white rounded-full hover:bg-green-700 active:scale-95 disabled:opacity-40"
            aria-label={t('chat.send')}
          >
            <IoSend className="w-5 h-5" />
          </button>
        </form>
        <p className="text-[10px] text-gray-400 text-center mt-1.5 leading-tight">
          ℹ️ {t('chat.disclaimer')}
        </p>
      </div>
    </div>
  );
}

