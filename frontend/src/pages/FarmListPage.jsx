import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { IoAdd, IoTrashOutline, IoCreateOutline } from 'react-icons/io5';
import { PiPlant } from 'react-icons/pi';
import api from '../api/axios';

export default function FarmListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [farms, setFarms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchFarms = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/farms');
      setFarms(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFarms();
  }, []);

  const handleDelete = async (farmId) => {
    if (!window.confirm(t('farm.confirmDelete'))) return;

    try {
      await api.delete(`/farms/${farmId}`);
      setFarms((prev) => prev.filter((f) => f.id !== farmId));
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    }
  };

  return (
    <div className="app-container pb-20">
      <header className="px-4 pt-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t('farm.title')}</h1>
        <button
          onClick={() => navigate('/farms/new')}
          className="bg-green-600 text-white p-3 rounded-full shadow-lg hover:bg-green-700 active:bg-green-800 transition-colors"
          aria-label={t('farm.addFarm')}
        >
          <IoAdd className="w-6 h-6" />
        </button>
      </header>

      <main className="px-4 mt-4">
        {/* Error */}
        {error && (
          <div
            className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-center mb-4"
            role="alert"
          >
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12" role="status">
            <div className="w-10 h-10 border-4 border-green-600 border-t-transparent rounded-full animate-spin" />
            <span className="sr-only">{t('common.loading')}</span>
          </div>
        )}

        {/* Empty state */}
        {!loading && farms.length === 0 && (
          <div className="text-center py-16">
            <PiPlant className="w-16 h-16 text-gray-300 mx-auto mb-4" aria-hidden="true" />
            <p className="text-xl font-medium text-gray-500">{t('farm.noFarms')}</p>
            <p className="text-base text-gray-400 mt-2">{t('farm.addFirst')}</p>
            <button
              onClick={() => navigate('/farms/new')}
              className="btn-primary mt-6 max-w-xs mx-auto"
              aria-label={t('farm.addFarm')}
            >
              {t('farm.addFarm')}
            </button>
          </div>
        )}

        {/* Farm list */}
        {!loading && farms.length > 0 && (
          <div className="space-y-3">
            {farms.map((farm) => (
              <article
                key={farm.id}
                className="card"
                aria-label={`${t('farm.farmName')}: ${farm.name}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-gray-900 truncate">
                      {farm.name}
                    </h3>
                    {farm.village && (
                      <p className="text-base text-gray-500 mt-0.5">
                        📍 {farm.village}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-gray-600">
                      {farm.size_acres && (
                        <span>📏 {farm.size_acres} {t('farm.sizeAcres').replace(/.*\(/, '').replace(')', '')}</span>
                      )}
                      {farm.crops && (
                        <span>🌾 {farm.crops}</span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 ml-2 flex-shrink-0">
                    <button
                      onClick={() => navigate(`/farms/${farm.id}/edit`)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      aria-label={`${t('farm.edit')} ${farm.name}`}
                    >
                      <IoCreateOutline className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(farm.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      aria-label={`${t('farm.delete')} ${farm.name}`}
                    >
                      <IoTrashOutline className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
