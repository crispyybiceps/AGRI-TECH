import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  IoArrowBack,
  IoShieldCheckmarkOutline,
  IoWarningOutline,
  IoCameraOutline,
  IoFlaskOutline,
  IoEyeOutline,
  IoCallOutline,
  IoLocationOutline,
  IoDocumentTextOutline,
  IoCheckmarkCircle,
} from 'react-icons/io5';
import { PiPlant } from 'react-icons/pi';
import api from '../api/axios';

export default function SoilPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);
  const [soilData, setSoilData] = useState(null);
  const [labsData, setLabsData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // overview, add_card, observation, guide
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Tier 1 Soil Card Form state
  const [cardForm, setCardForm] = useState({
    ph: '',
    ec: '',
    oc: '',
    n: '',
    p: '',
    k: '',
    crop: '',
  });

  // Tier 3 Visual Observation Form state
  const [obsForm, setObsForm] = useState({
    color: 'black_dark',
    texture: 'clay_sticky',
    drainage: 'moderate_24h',
    cracking: 'deep_cracks',
    symptom: 'none',
  });

  // Load farms & labs directory
  useEffect(() => {
    const init = async () => {
      try {
        const [farmRes, labsRes] = await Promise.all([
          api.get('/farms'),
          api.get('/soil/labs'),
        ]);
        setFarms(farmRes.data);
        setLabsData(labsRes.data);
        if (farmRes.data.length > 0) {
          setSelectedFarmId(farmRes.data[0].id);
        }
      } catch (err) {
        setError(t('common.error'));
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Fetch soil insights for selected farm
  useEffect(() => {
    if (selectedFarmId) {
      loadSoilInsights(selectedFarmId);
    }
  }, [selectedFarmId]);

  const loadSoilInsights = async (farmId) => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/soil/${farmId}`);
      setSoilData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  // Mock OCR Auto-fill
  const handleSimulateOcr = async () => {
    try {
      const res = await api.post('/soil/ocr-stub');
      const vals = res.data.extracted_values;
      setCardForm((prev) => ({
        ...prev,
        ph: vals.ph || '',
        ec: vals.ec || '',
        oc: vals.oc || '',
        n: vals.n || '',
        p: vals.p || '',
        k: vals.k || '',
      }));
      setMessage('✅ ' + res.data.message);
    } catch (err) {
      setError('OCR simulation failed');
    }
  };

  // Submit Tier 1 Soil Card
  const handleSubmitCard = async (e) => {
    e.preventDefault();
    if (!selectedFarmId) return;
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        ph: cardForm.ph ? parseFloat(cardForm.ph) : null,
        ec: cardForm.ec ? parseFloat(cardForm.ec) : null,
        oc: cardForm.oc ? parseFloat(cardForm.oc) : null,
        n: cardForm.n ? parseFloat(cardForm.n) : null,
        p: cardForm.p ? parseFloat(cardForm.p) : null,
        k: cardForm.k ? parseFloat(cardForm.k) : null,
        crop: cardForm.crop || null,
      };
      await api.post(`/soil/card/${selectedFarmId}`, payload);
      setMessage(t('soil.saveCard') + ' ✅');
      await loadSoilInsights(selectedFarmId);
      setActiveTab('overview');
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Tier 3 Observation
  const handleSubmitObservation = async (e) => {
    e.preventDefault();
    if (!selectedFarmId) return;
    setSubmitting(true);
    setError('');
    try {
      await api.post(`/soil/observation/${selectedFarmId}`, obsForm);
      await loadSoilInsights(selectedFarmId);
      setActiveTab('overview');
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setSubmitting(false);
    }
  };

  // Fetch Tier 2 SoilGrids estimate
  const handleFetchSoilGrids = async () => {
    if (!selectedFarmId) return;
    setLoading(true);
    try {
      await api.get(`/soil/soilgrids/${selectedFarmId}`);
      await loadSoilInsights(selectedFarmId);
      setActiveTab('overview');
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const primary = soilData?.primary_insight;

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
          <h1 className="text-2xl font-bold text-gray-900">{t('soil.title')}</h1>
        </div>
      </header>

      {/* Farm Switcher */}
      <div className="px-4 mt-3">
        {farms.length > 0 ? (
          <div className="bg-gray-100 p-1.5 rounded-xl flex items-center gap-2">
            <span className="text-sm font-medium text-gray-600 pl-2">
              {t('soil.selectFarm')}:
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
            ⚠️ Please add a farm first from the Farms tab.
          </div>
        )}
      </div>

      {/* 4 Action Navigation Tabs */}
      <div className="px-4 mt-3">
        <div className="grid grid-cols-4 gap-1.5 bg-gray-100 p-1 rounded-2xl text-xs font-semibold text-center">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'overview'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📊 {t('home')}
          </button>
          <button
            onClick={() => setActiveTab('add_card')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'add_card'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            🧪 {t('soil.addCard')}
          </button>
          <button
            onClick={() => setActiveTab('observation')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'observation'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            👁️ {t('soil.guidedObservation')}
          </button>
          <button
            onClick={() => setActiveTab('guide')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'guide'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            🏛️ {t('soil.labsDirectory')}
          </button>
        </div>
      </div>

      {/* Main Tab Panels */}
      <main className="px-4 mt-4 space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-center text-sm">
            {error}
          </div>
        )}
        {message && (
          <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-xl text-center text-sm font-medium">
            {message}
          </div>
        )}

        {/* ──────────────────────────────────────────────
            TAB 1: OVERVIEW & HIGHEST CONFIDENCE INSIGHT
           ────────────────────────────────────────────── */}
        {activeTab === 'overview' && (
          <>
            {loading ? (
              <div className="flex justify-center py-16">
                <div className="w-12 h-12 border-4 border-green-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : primary ? (
              <div className="space-y-4">
                {/* Confidence Badge Hero Card */}
                <div
                  className={`rounded-3xl p-5 text-white shadow-xl ${
                    primary.tier === 1
                      ? 'bg-gradient-to-br from-green-700 to-emerald-900'
                      : primary.tier === 2
                      ? 'bg-gradient-to-br from-amber-600 to-amber-800'
                      : 'bg-gradient-to-br from-blue-700 to-indigo-900'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs uppercase font-extrabold px-3 py-1 rounded-full tracking-wider ${
                        primary.tier === 1
                          ? 'bg-green-500 text-white'
                          : primary.tier === 2
                          ? 'bg-amber-400 text-amber-950'
                          : 'bg-blue-400 text-blue-950'
                      }`}
                    >
                      {primary.confidence === 'High'
                        ? t('soil.confidenceHigh')
                        : primary.confidence === 'Medium' || primary.tier === 2
                        ? t('soil.confidenceMedium')
                        : t('soil.confidenceLow')}
                    </span>
                    <span className="text-xs text-white/80 font-medium">
                      Tier {primary.tier}
                    </span>
                  </div>

                  <h2 className="text-xl font-bold mt-3 leading-snug">
                    {primary.source}
                  </h2>
                  <p className="text-xs text-white/80 mt-0.5">
                    {new Date(primary.created_at).toLocaleDateString(
                      i18n.language === 'mr' ? 'mr-IN' : 'hi-IN'
                    )}
                  </p>

                  {/* Tier 2 & 3 Disclaimer banner */}
                  {primary.tier !== 1 && (
                    <div className="bg-black/20 border border-white/20 p-2.5 rounded-xl text-xs mt-3 text-white font-medium">
                      ⚠️ {t('soil.notLabTestNotice')}
                    </div>
                  )}
                </div>

                {/* TIER 1 PARAMETERS BREAKDOWN */}
                {primary.tier === 1 && primary.interpretation?.parameters && (
                  <div className="card space-y-3">
                    <h3 className="text-base font-bold text-gray-900">
                      🧪 Lab Test Values
                    </h3>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {Object.entries(primary.interpretation.parameters).map(
                        ([k, param]) => (
                          <div
                            key={k}
                            className="bg-gray-50 p-2.5 rounded-xl border border-gray-100 flex flex-col justify-between"
                          >
                            <span className="text-xs text-gray-500 font-medium">
                              {param.name}
                            </span>
                            <div className="flex items-baseline justify-between mt-1">
                              <span className="text-lg font-extrabold text-gray-900">
                                {param.value}{' '}
                                <span className="text-xs font-normal text-gray-500">
                                  {param.unit}
                                </span>
                              </span>
                              <span
                                className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                                  param.color === 'green'
                                    ? 'bg-green-100 text-green-800'
                                    : param.color === 'red'
                                    ? 'bg-red-100 text-red-800'
                                    : 'bg-amber-100 text-amber-800'
                                }`}
                              >
                                {param[`status_${i18n.language}`] || param.status}
                              </span>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}

                {/* TIER 1 AMENDMENTS */}
                {primary.tier === 1 &&
                  primary.interpretation?.amendments?.length > 0 && (
                    <div className="card bg-amber-50/70 border-amber-200">
                      <h3 className="text-base font-bold text-amber-900 mb-2">
                        ⚖️ {t('soil.amendmentsTitle')}
                      </h3>
                      <div className="space-y-2 text-sm">
                        {primary.interpretation.amendments.map((am, i) => (
                          <div
                            key={i}
                            className="bg-white p-3 rounded-xl border border-amber-200"
                          >
                            <span className="font-bold text-amber-800 text-xs block mb-1">
                              {am.condition}
                            </span>
                            <p className="text-gray-700 text-xs font-medium leading-relaxed">
                              {am[`advice_${i18n.language}`] || am.advice_en}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {/* TIER 1 FERTILIZER ADJUSTMENTS */}
                {primary.tier === 1 &&
                  primary.interpretation?.fertilizer_adjustments?.length > 0 && (
                    <div className="card bg-green-50/70 border-green-200">
                      <h3 className="text-base font-bold text-green-900 mb-2">
                        🌱 {t('soil.fertilizerTitle')}
                      </h3>
                      <div className="space-y-2 text-sm">
                        {primary.interpretation.fertilizer_adjustments.map((fa, i) => (
                          <div
                            key={i}
                            className="bg-white p-3 rounded-xl border border-green-200"
                          >
                            <span className="font-bold text-green-800 text-xs block mb-1">
                              {fa.nutrient}
                            </span>
                            <p className="text-gray-700 text-xs font-medium leading-relaxed">
                              {fa[`advice_${i18n.language}`] || fa.advice_en}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {/* TIER 2 SOILGRIDS RESULTS */}
                {primary.tier === 2 && (
                  <div className="card space-y-3">
                    <h3 className="text-base font-bold text-gray-900">
                      🛰️ Model Estimated Properties
                    </h3>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      {primary.interpretation?.estimated_properties &&
                        Object.entries(primary.interpretation.estimated_properties).map(
                          ([k, prop]) => (
                            <div
                              key={k}
                              className="bg-gray-50 p-3 rounded-xl border border-gray-100"
                            >
                              <span className="text-xs text-gray-500 capitalize">
                                {k.replace(/_/g, ' ')}
                              </span>
                              <p className="text-base font-bold text-gray-900 mt-0.5">
                                {prop.value}
                              </p>
                              <p className="text-xs text-amber-800 font-medium">
                                {prop.label}
                              </p>
                            </div>
                          )
                        )}
                    </div>
                    <div className="bg-amber-50 p-3 rounded-xl border border-amber-200 text-xs text-gray-700 mt-2">
                      <span className="font-bold text-amber-900 block mb-1">
                        General Soil Management:
                      </span>
                      {primary.interpretation?.general_management_advice?.[i18n.language] ||
                        primary.interpretation?.general_management_advice?.en}
                    </div>
                  </div>
                )}

                {/* TIER 3 OBSERVATION INDICATIONS */}
                {primary.tier === 3 && (
                  <div className="card space-y-3">
                    <h3 className="text-base font-bold text-gray-900">
                      🔍 Field Indications (Observation)
                    </h3>
                    <div className="space-y-2">
                      {primary.interpretation?.indications?.map((ind, i) => (
                        <div
                          key={i}
                          className="bg-blue-50 border border-blue-200 p-3 rounded-xl text-xs font-medium text-blue-950"
                        >
                          {ind[i18n.language] || ind.en}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* EMPTY STATE: No records yet */
              <div className="text-center py-8 card border-dashed border-2">
                <PiPlant className="w-16 h-16 text-gray-300 mx-auto mb-2" />
                <h3 className="text-lg font-bold text-gray-800 mb-1">
                  {t('soil.noRecords')}
                </h3>
                <p className="text-xs text-gray-500 max-w-xs mx-auto mb-4">
                  Choose an option below to analyze your farm's soil:
                </p>

                <div className="grid grid-cols-1 gap-2.5 max-w-sm mx-auto text-left">
                  <button
                    onClick={() => setActiveTab('add_card')}
                    className="p-3 bg-green-50 border border-green-200 rounded-xl hover:bg-green-100 flex items-center gap-3"
                  >
                    <span className="text-3xl">🧪</span>
                    <div>
                      <span className="font-bold text-green-900 text-sm block">
                        Tier 1: Enter Soil Health Card
                      </span>
                      <span className="text-xs text-green-700">
                        Official certified lab test results (High Confidence)
                      </span>
                    </div>
                  </button>

                  <button
                    onClick={() => setActiveTab('observation')}
                    className="p-3 bg-blue-50 border border-blue-200 rounded-xl hover:bg-blue-100 flex items-center gap-3"
                  >
                    <span className="text-3xl">👁️</span>
                    <div>
                      <span className="font-bold text-blue-900 text-sm block">
                        Tier 3: Guided Field Observation
                      </span>
                      <span className="text-xs text-blue-700">
                        Inspect color, texture, cracking & leaf signs
                      </span>
                    </div>
                  </button>

                  <button
                    onClick={handleFetchSoilGrids}
                    className="p-3 bg-amber-50 border border-amber-200 rounded-xl hover:bg-amber-100 flex items-center gap-3"
                  >
                    <span className="text-3xl">🛰️</span>
                    <div>
                      <span className="font-bold text-amber-900 text-sm block">
                        Tier 2: Model Estimate (SoilGrids)
                      </span>
                      <span className="text-xs text-amber-700">
                        Satellite geological estimate (ESTIMATE only)
                      </span>
                    </div>
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* ──────────────────────────────────────────────
            TAB 2: ENTER SOIL HEALTH CARD (TIER 1)
           ────────────────────────────────────────────── */}
        {activeTab === 'add_card' && (
          <form onSubmit={handleSubmitCard} className="card space-y-4">
            <div className="flex items-center justify-between border-b pb-2">
              <h2 className="text-base font-bold text-gray-900">
                🧪 {t('soil.addCard')} (Tier 1 - High)
              </h2>
              <button
                type="button"
                onClick={handleSimulateOcr}
                className="flex items-center gap-1.5 text-xs font-bold text-green-800 bg-green-100 px-3 py-1.5 rounded-lg active:scale-95 shadow-xs"
              >
                <IoCameraOutline className="w-4 h-4" />
                <span>{t('soil.simulateOcr')}</span>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t('soil.ph')} (3.0 - 10.0)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="3"
                  max="10"
                  value={cardForm.ph}
                  onChange={(e) =>
                    setCardForm({ ...cardForm, ph: e.target.value })
                  }
                  placeholder="e.g. 7.2"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t('soil.ec')} (dS/m)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={cardForm.ec}
                  onChange={(e) =>
                    setCardForm({ ...cardForm, ec: e.target.value })
                  }
                  placeholder="e.g. 0.35"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t('soil.oc')} (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="5"
                  value={cardForm.oc}
                  onChange={(e) =>
                    setCardForm({ ...cardForm, oc: e.target.value })
                  }
                  placeholder="e.g. 0.55"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t('soil.n')} (kg/ha)
                </label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={cardForm.n}
                  onChange={(e) =>
                    setCardForm({ ...cardForm, n: e.target.value })
                  }
                  placeholder="e.g. 240"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t('soil.p')} (kg/ha)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={cardForm.p}
                  onChange={(e) =>
                    setCardForm({ ...cardForm, p: e.target.value })
                  }
                  placeholder="e.g. 18.5"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t('soil.k')} (kg/ha)
                </label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  value={cardForm.k}
                  onChange={(e) =>
                    setCardForm({ ...cardForm, k: e.target.value })
                  }
                  placeholder="e.g. 210"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Intended Crop for Fertilizer Advice
              </label>
              <input
                type="text"
                value={cardForm.crop}
                onChange={(e) =>
                  setCardForm({ ...cardForm, crop: e.target.value })
                }
                placeholder="e.g. Sugarcane, Cotton, Soybean"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !cardForm.ph}
              className="btn-primary"
            >
              {submitting ? t('common.loading') : t('soil.saveCard')}
            </button>
          </form>
        )}

        {/* ──────────────────────────────────────────────
            TAB 3: GUIDED OBSERVATION (TIER 3)
           ────────────────────────────────────────────── */}
        {activeTab === 'observation' && (
          <form onSubmit={handleSubmitObservation} className="card space-y-4">
            <div className="border-b pb-2">
              <h2 className="text-base font-bold text-gray-900">
                👁️ {t('soil.guidedObservation')} (Tier 3 - Low)
              </h2>
              <p className="text-xs text-amber-800 font-medium mt-0.5">
                ⚠️ Outputs 'Possible indication of...', NOT a lab diagnosis.
              </p>
            </div>

            {/* 1. Color */}
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1.5">
                1. Soil Color in Field:
              </label>
              <select
                value={obsForm.color}
                onChange={(e) =>
                  setObsForm({ ...obsForm, color: e.target.value })
                }
                className="text-sm"
              >
                <option value="black_dark">⬛ Deep Black / Dark Brown (काळी माती)</option>
                <option value="red">🟥 Red / Brownish Red (तांबडी माती)</option>
                <option value="pale_yellow">🟨 Pale Yellowish / Washed Out (पिवळसर / हलकी)</option>
                <option value="grey_white_crust">⬜ Grey with White Salt Crust (पांढरा क्षार थर)</option>
              </select>
            </div>

            {/* 2. Texture */}
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1.5">
                2. Feel / Texture when Moist:
              </label>
              <select
                value={obsForm.texture}
                onChange={(e) =>
                  setObsForm({ ...obsForm, texture: e.target.value })
                }
                className="text-sm"
              >
                <option value="clay_sticky">Sticky clay, rolls into a thin ribbon (चिकट / भारी माती)</option>
                <option value="loamy_crumbly">Crumbly, soft loam, holds together well (मध्यम / सुपीक पोत)</option>
                <option value="sandy_loose">Gritty and rough, falls apart quickly (रेताड / हलकी जमीन)</option>
              </select>
            </div>

            {/* 3. Drainage */}
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1.5">
                3. Water Drainage After Rain:
              </label>
              <select
                value={obsForm.drainage}
                onChange={(e) =>
                  setObsForm({ ...obsForm, drainage: e.target.value })
                }
                className="text-sm"
              >
                <option value="moderate_24h">Drains normally within 24 hours (योग्य निचरा)</option>
                <option value="waterlogs">Water stands for 2+ days (पाणी साचून राहते)</option>
                <option value="rapid_draining">Dries out very quickly within hours (पाणी टिकत नाही)</option>
              </select>
            </div>

            {/* 4. Cracking */}
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1.5">
                4. Cracking in Dry Season:
              </label>
              <select
                value={obsForm.cracking}
                onChange={(e) =>
                  setObsForm({ ...obsForm, cracking: e.target.value })
                }
                className="text-sm"
              >
                <option value="deep_cracks">Deep, wide cracks open up (मोठ्या भेगा पडतात)</option>
                <option value="slight_cracks">Fine hairline surface cracks (बारीक भेगा)</option>
                <option value="no_cracks">No visible cracking (भेगा पडत नाहीत)</option>
              </select>
            </div>

            {/* 5. Crop Symptoms */}
            <div>
              <label className="block text-xs font-bold text-gray-800 mb-1.5">
                5. Visible Crop Leaves Signs (If growing):
              </label>
              <select
                value={obsForm.symptom}
                onChange={(e) =>
                  setObsForm({ ...obsForm, symptom: e.target.value })
                }
                className="text-sm"
              >
                <option value="none">Healthy green leaves (पाने निरोगी हिरवी आहेत)</option>
                <option value="yellow_lower_leaves">Yellowing lower leaves (खालची जुनी पाने पिवळी पडणे)</option>
                <option value="purple_stems_leaves">Purple/reddish tint on stems & leaves (जांभळट/तांबूस छटा)</option>
                <option value="burnt_leaf_edges">Brown scorched leaf tips & margins (पानांच्या कडा जळाल्यासारख्या)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="btn-primary"
            >
              {submitting ? t('common.loading') : t('soil.submitObservation')}
            </button>
          </form>
        )}

        {/* ──────────────────────────────────────────────
            TAB 4: SOIL SAMPLING GUIDE & MAHARASHTRA LABS (TIER 5)
           ────────────────────────────────────────────── */}
        {activeTab === 'guide' && (
          <div className="space-y-4">
            {/* 5 Steps Guide */}
            <div className="card space-y-3">
              <div className="flex items-center gap-2 border-b pb-2">
                <span className="text-2xl">📐</span>
                <h2 className="text-base font-bold text-gray-900">
                  {t('soil.sampleGuide')}
                </h2>
              </div>

              <div className="space-y-2.5">
                {labsData?.collection_steps?.map((step) => (
                  <div
                    key={step.step}
                    className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex items-start gap-3"
                  >
                    <span className="w-6 h-6 rounded-full bg-green-600 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                      {step.step}
                    </span>
                    <div>
                      <h4 className="text-sm font-bold text-gray-900">
                        {step[`title_${i18n.language}`] || step.title_en}
                      </h4>
                      <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                        {step[`desc_${i18n.language}`] || step.desc_en}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Labs Directory */}
            <div className="card space-y-3">
              <div className="flex items-center gap-2 border-b pb-2">
                <span className="text-2xl">🏛️</span>
                <h2 className="text-base font-bold text-gray-900">
                  {t('soil.labsDirectory')}
                </h2>
              </div>
              <p className="text-xs text-gray-500 italic">
                {labsData?.notice || 'Accredited testing labs in Maharashtra.'}
              </p>

              <div className="space-y-2.5">
                {labsData?.labs?.map((lab, i) => (
                  <div
                    key={i}
                    className="p-3 bg-white border border-gray-200 rounded-xl shadow-xs"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[11px] font-bold text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                          📍 {lab[`district_${i18n.language}`] || lab.district}
                        </span>
                        <h4 className="text-sm font-bold text-gray-900 mt-1.5 leading-snug">
                          {i18n.language === 'mr' ? lab.name_mr : lab.name}
                        </h4>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {lab.location}
                        </p>
                      </div>
                      <a
                        href={`tel:${lab.contact}`}
                        className="p-2 bg-green-100 text-green-800 rounded-full hover:bg-green-200 active:scale-95 flex-shrink-0"
                        aria-label={`Call ${lab.name}`}
                      >
                        <IoCallOutline className="w-5 h-5" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

