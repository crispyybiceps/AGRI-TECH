import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  IoArrowBack,
  IoVolumeHighOutline,
  IoStopCircleOutline,
  IoWarningOutline,
  IoCloudOfflineOutline,
  IoCheckmarkCircleOutline,
  IoInformationCircleOutline,
} from 'react-icons/io5';
import api from '../api/axios';

const WEATHER_EMOJIS = {
  0: '☀️',
  1: '🌤️',
  2: '⛅',
  3: '☁️',
  45: '🌫️',
  51: '🌦️',
  61: '🌧️',
  63: '🌧️',
  65: '⛈️',
  80: '🌦️',
  95: '⚡',
};

export default function WeatherPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [advisoryData, setAdvisoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);

  const synthRef = useRef(window.speechSynthesis);

  // 1. Fetch user farms
  useEffect(() => {
    const fetchFarms = async () => {
      try {
        const res = await api.get('/farms');
        setFarms(res.data);
        if (res.data.length > 0) {
          setSelectedFarmId(res.data[0].id);
        } else {
          // If no farms, load general weather
          loadGeneralWeather();
        }
      } catch (err) {
        loadGeneralWeather();
      }
    };
    fetchFarms();
  }, []);

  // 2. Fetch weather & advisory when selected farm changes
  useEffect(() => {
    if (selectedFarmId) {
      loadFarmWeather(selectedFarmId);
    }
  }, [selectedFarmId]);

  const loadFarmWeather = async (farmId) => {
    setLoading(true);
    setError('');
    stopAudio();
    try {
      const [wRes, aRes] = await Promise.all([
        api.get(`/weather/${farmId}`),
        api.get(`/advisory/${farmId}`),
      ]);
      setWeatherData(wRes.data);
      setAdvisoryData(aRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const loadGeneralWeather = async () => {
    setLoading(true);
    setError('');
    stopAudio();
    try {
      const res = await api.get('/weather-general');
      setWeatherData(res.data);
      setAdvisoryData(null);
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  // Text-To-Speech (Web Speech API)
  const handleReadAloud = () => {
    if (!synthRef.current) {
      alert('Text-to-speech is not supported on this device/browser.');
      return;
    }

    if (isSpeaking) {
      stopAudio();
      return;
    }

    const langCode = i18n.language === 'mr' ? 'mr-IN' : i18n.language === 'hi' ? 'hi-IN' : 'en-US';
    let textToSpeak = '';

    const currentTemp = weatherData?.current?.temperature_2m;
    const currentCode = weatherData?.current?.weather_code ?? 0;
    const weatherDesc = weatherData?.weather_codes_map?.[currentCode]?.[i18n.language] || '';

    if (i18n.language === 'mr') {
      textToSpeak += `सध्याचे तापमान ${Math.round(currentTemp || 30)} अंश सेल्सिअस असून ${weatherDesc} आहे. `;
    } else if (i18n.language === 'hi') {
      textToSpeak += `वर्तमान तापमान ${Math.round(currentTemp || 30)} डिग्री सेल्सियस है और ${weatherDesc} है। `;
    } else {
      textToSpeak += `Current temperature is ${Math.round(currentTemp || 30)} degrees Celsius with ${weatherDesc}. `;
    }

    if (advisoryData?.advisories && advisoryData.advisories.length > 0) {
      advisoryData.advisories.forEach((adv) => {
        const title = adv[`title_${i18n.language}`] || adv.title_en;
        const action = adv[`action_${i18n.language}`] || adv.action_en;
        textToSpeak += `${title}. ${action} `;
      });
    }

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = langCode;
    utterance.rate = 0.9; // slightly slower for rural users

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    synthRef.current.cancel();
    synthRef.current.speak(utterance);
    setIsSpeaking(true);
  };

  const stopAudio = () => {
    if (synthRef.current) {
      synthRef.current.cancel();
    }
    setIsSpeaking(false);
  };

  useEffect(() => {
    return () => {
      stopAudio();
    };
  }, []);

  const currentConditionCode = weatherData?.current?.weather_code ?? 0;
  const currentEmoji = WEATHER_EMOJIS[currentConditionCode] || '🌤️';
  const currentDesc = weatherData?.weather_codes_map?.[currentConditionCode]?.[i18n.language] || '';

  return (
    <div className="app-container pb-24">
      {/* Top Header */}
      <header className="px-4 pt-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="p-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label={t('common.back')}
          >
            <IoArrowBack className="w-6 h-6" />
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{t('weather.title')}</h1>
        </div>

        {/* Read aloud Voice button */}
        <button
          onClick={handleReadAloud}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold transition-all shadow-sm ${
            isSpeaking
              ? 'bg-red-600 text-white animate-pulse'
              : 'bg-green-100 text-green-800 hover:bg-green-200 active:scale-95'
          }`}
          aria-label={isSpeaking ? t('weather.stopReading') : t('weather.readAloud')}
        >
          {isSpeaking ? (
            <>
              <IoStopCircleOutline className="w-5 h-5" />
              <span>{t('weather.stopReading')}</span>
            </>
          ) : (
            <>
              <IoVolumeHighOutline className="w-5 h-5 text-green-700" />
              <span>{t('weather.readAloud')}</span>
            </>
          )}
        </button>
      </header>

      {/* Farm Switcher */}
      <div className="px-4 mt-3">
        {farms.length > 0 ? (
          <div className="bg-gray-100 p-1.5 rounded-xl flex items-center gap-2">
            <span className="text-sm font-medium text-gray-600 pl-2">
              {t('weather.selectFarm')}:
            </span>
            <select
              value={selectedFarmId || ''}
              onChange={(e) => setSelectedFarmId(Number(e.target.value))}
              className="bg-white border-0 text-base font-semibold text-gray-800 py-1.5 px-3 rounded-lg focus:ring-2 focus:ring-green-500 shadow-sm flex-1"
            >
              {farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name} ({farm.village})
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="text-sm text-gray-600 bg-gray-100 p-2 rounded-lg text-center font-medium">
            📍 {t('weather.allMaharashtra')}
          </div>
        )}
      </div>

      {/* Offline / Cache indicator */}
      {weatherData && (
        <div className="px-4 mt-2">
          {weatherData.cached ? (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-1.5 rounded-lg">
              <IoCloudOfflineOutline className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span>{t('weather.cachedNotice')}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-gray-500 px-1">
              <IoCheckmarkCircleOutline className="w-3.5 h-3.5 text-green-600" />
              <span>{t('weather.liveNotice')}</span>
            </div>
          )}
        </div>
      )}

      {/* Main Content */}
      <main className="px-4 mt-3 space-y-4">
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-12 h-12 border-4 border-green-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-center">
            {error}
          </div>
        ) : (
          <>
            {/* Current Weather Card */}
            <div className="bg-gradient-to-br from-green-700 to-green-900 text-white rounded-3xl p-6 shadow-xl relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-green-200">
                    {t('weather.currentTemp')}
                  </p>
                  <div className="text-6xl font-extrabold tracking-tight mt-1">
                    {Math.round(weatherData?.current?.temperature_2m ?? 30)}°
                    <span className="text-3xl font-light">C</span>
                  </div>
                  <p className="text-lg font-semibold text-green-100 mt-1 capitalize">
                    {currentDesc}
                  </p>
                </div>
                <div className="text-7xl p-2 select-none filter drop-shadow-md">
                  {currentEmoji}
                </div>
              </div>

              {/* 3 Metric Pills */}
              <div className="grid grid-cols-3 gap-2 mt-6 pt-4 border-t border-green-600/60 text-center">
                <div className="bg-green-800/60 p-2.5 rounded-xl">
                  <p className="text-xs text-green-200">{t('weather.humidity')}</p>
                  <p className="text-lg font-bold mt-0.5">
                    {weatherData?.current?.relative_humidity_2m ?? 60}%
                  </p>
                </div>
                <div className="bg-green-800/60 p-2.5 rounded-xl">
                  <p className="text-xs text-green-200">{t('weather.windSpeed')}</p>
                  <p className="text-lg font-bold mt-0.5">
                    {Math.round(weatherData?.current?.wind_speed_10m ?? 10)} km/h
                  </p>
                </div>
                <div className="bg-green-800/60 p-2.5 rounded-xl">
                  <p className="text-xs text-green-200">{t('weather.rainChance')}</p>
                  <p className="text-lg font-bold mt-0.5">
                    {weatherData?.daily?.precipitation_probability_max?.[0] ?? 0}%
                  </p>
                </div>
              </div>
            </div>

            {/* Agricultural Advisory Section */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-bold text-gray-900">
                  {t('weather.advisoryTitle')}
                </h2>
              </div>

              {advisoryData?.advisories && advisoryData.advisories.length > 0 ? (
                <div className="space-y-3">
                  {advisoryData.advisories.map((adv, idx) => {
                    const isWarning = adv.type === 'warning';
                    const isCaution = adv.type === 'caution';
                    const title = adv[`title_${i18n.language}`] || adv.title_en;
                    const action = adv[`action_${i18n.language}`] || adv.action_en;

                    return (
                      <div
                        key={idx}
                        className={`p-4 rounded-2xl border transition-all ${
                          isWarning
                            ? 'bg-red-50 border-red-300 text-red-900 shadow-sm'
                            : isCaution
                            ? 'bg-amber-50 border-amber-300 text-amber-900 shadow-sm'
                            : 'bg-green-50 border-green-300 text-green-900 shadow-sm'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-3xl flex-shrink-0" aria-hidden="true">
                            {adv.icon}
                          </span>
                          <div className="flex-1">
                            <h3 className="text-base font-bold leading-tight">{title}</h3>
                            <p className="text-sm font-medium mt-1 leading-relaxed opacity-90">
                              {action}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl text-center text-sm text-gray-600">
                  <IoInformationCircleOutline className="w-6 h-6 text-gray-400 mx-auto mb-1" />
                  {t('weather.noAdvisories')}
                </div>
              )}
            </div>

            {/* 7-Day Forecast Strip */}
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-2">
                {t('weather.forecast7Days')}
              </h2>
              <div className="space-y-2">
                {weatherData?.daily?.time?.map((dateStr, idx) => {
                  const code = weatherData.daily.weather_code[idx];
                  const maxT = Math.round(weatherData.daily.temperature_2m_max[idx]);
                  const minT = Math.round(weatherData.daily.temperature_2m_min[idx]);
                  const rainP = weatherData.daily.precipitation_probability_max[idx];
                  const rainSum = weatherData.daily.precipitation_sum[idx];
                  const emoji = WEATHER_EMOJIS[code] || '🌤️';

                  const dayName =
                    idx === 0
                      ? t('weather.today')
                      : new Date(dateStr).toLocaleDateString(
                          i18n.language === 'mr' ? 'mr-IN' : i18n.language === 'hi' ? 'hi-IN' : 'en-IN',
                          { weekday: 'short', day: 'numeric', month: 'short' }
                        );

                  return (
                    <div
                      key={dateStr}
                      className="flex items-center justify-between p-3.5 bg-white border border-gray-200 rounded-xl shadow-xs"
                    >
                      <span className="font-semibold text-gray-800 text-base w-28">
                        {dayName}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl" aria-hidden="true">
                          {emoji}
                        </span>
                        {rainP > 20 && (
                          <span className="text-xs font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                            💧 {rainP}%
                          </span>
                        )}
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-gray-900 text-base">{maxT}°</span>
                        <span className="text-gray-400 text-sm ml-1.5 font-medium">{minT}°</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Seasonal Crop & Seed Suggestions */}
            {advisoryData?.crop_suggestions && (
              <div className="card mt-2 bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">🌾</span>
                  <h2 className="text-base font-bold text-amber-900">
                    {t('weather.cropGuide')}
                  </h2>
                </div>
                <p className="text-xs text-amber-800 font-semibold mb-3">
                  🏷️ {advisoryData.crop_suggestions.season_name?.[i18n.language] || ''}
                </p>

                <div className="space-y-2">
                  {advisoryData.crop_suggestions.crops?.map((crop, idx) => (
                    <div
                      key={idx}
                      className="bg-white/80 p-2.5 rounded-lg border border-amber-100 text-xs"
                    >
                      <div className="flex justify-between font-bold text-gray-900 text-sm">
                        <span>{crop[`name_${i18n.language}`] || crop.name_en}</span>
                        <span className="text-green-700 font-medium text-xs">
                          {crop.recommended_varieties}
                        </span>
                      </div>
                      <p className="text-gray-600 mt-1">{crop.sowing_condition}</p>
                    </div>
                  ))}
                </div>

                <p className="text-[11px] text-gray-500 italic mt-3 text-center border-t border-amber-200/60 pt-2">
                  ⚠️ {advisoryData.crop_suggestions.disclaimer}
                </p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

