import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { IoArrowBack } from 'react-icons/io5';
import api from '../api/axios';

export default function FarmFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditing = !!id;

  const [form, setForm] = useState({
    name: '',
    village: '',
    latitude: '',
    longitude: '',
    size_acres: '',
    crops: '',
  });
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(isEditing);
  const [error, setError] = useState('');

  // Fetch farm data when editing
  useEffect(() => {
    if (isEditing) {
      const fetchFarm = async () => {
        try {
          const res = await api.get(`/farms/${id}`);
          const farm = res.data;
          setForm({
            name: farm.name || '',
            village: farm.village || '',
            latitude: farm.latitude ?? '',
            longitude: farm.longitude ?? '',
            size_acres: farm.size_acres ?? '',
            crops: farm.crops || '',
          });
        } catch (err) {
          setError(err.response?.data?.detail || t('common.error'));
        } finally {
          setFetching(false);
        }
      };
      fetchFarm();
    }
  }, [id]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const payload = {
      name: form.name,
      village: form.village || null,
      latitude: form.latitude ? parseFloat(form.latitude) : null,
      longitude: form.longitude ? parseFloat(form.longitude) : null,
      size_acres: form.size_acres ? parseFloat(form.size_acres) : null,
      crops: form.crops || null,
    };

    try {
      if (isEditing) {
        await api.put(`/farms/${id}`, payload);
      } else {
        await api.post('/farms', payload);
      }
      navigate('/farms', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="app-container flex items-center justify-center min-h-screen" role="status">
        <div className="w-10 h-10 border-4 border-green-600 border-t-transparent rounded-full animate-spin" />
        <span className="sr-only">{t('common.loading')}</span>
      </div>
    );
  }

  return (
    <div className="app-container pb-20">
      {/* Header */}
      <header className="px-4 pt-4 flex items-center gap-3">
        <button
          onClick={() => navigate('/farms')}
          className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          aria-label={t('common.back')}
        >
          <IoArrowBack className="w-6 h-6" />
        </button>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEditing ? t('farm.editFarm') : t('farm.addFarm')}
        </h1>
      </header>

      <main className="px-4 mt-6">
        {/* Error */}
        {error && (
          <div
            className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-center mb-4"
            role="alert"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Farm Name */}
          <div>
            <label
              htmlFor="farm-name"
              className="block text-base font-medium text-gray-700 mb-2"
            >
              {t('farm.farmName')} *
            </label>
            <input
              id="farm-name"
              type="text"
              value={form.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder={t('farm.farmNamePlaceholder')}
              aria-label={t('farm.farmName')}
              required
            />
          </div>

          {/* Village */}
          <div>
            <label
              htmlFor="farm-village"
              className="block text-base font-medium text-gray-700 mb-2"
            >
              {t('farm.village')}
            </label>
            <input
              id="farm-village"
              type="text"
              value={form.village}
              onChange={(e) => handleChange('village', e.target.value)}
              placeholder={t('farm.villagePlaceholder')}
              aria-label={t('farm.village')}
            />
          </div>

          {/* Size */}
          <div>
            <label
              htmlFor="farm-size"
              className="block text-base font-medium text-gray-700 mb-2"
            >
              {t('farm.sizeAcres')}
            </label>
            <input
              id="farm-size"
              type="number"
              inputMode="decimal"
              step="0.01"
              min="0"
              value={form.size_acres}
              onChange={(e) => handleChange('size_acres', e.target.value)}
              placeholder={t('farm.sizePlaceholder')}
              aria-label={t('farm.sizeAcres')}
            />
          </div>

          {/* Crops */}
          <div>
            <label
              htmlFor="farm-crops"
              className="block text-base font-medium text-gray-700 mb-2"
            >
              {t('farm.crops')}
            </label>
            <input
              id="farm-crops"
              type="text"
              value={form.crops}
              onChange={(e) => handleChange('crops', e.target.value)}
              placeholder={t('farm.cropsPlaceholder')}
              aria-label={t('farm.crops')}
            />
          </div>

          {/* Latitude */}
          <div>
            <label
              htmlFor="farm-lat"
              className="block text-base font-medium text-gray-700 mb-2"
            >
              {t('farm.latitude')}
            </label>
            <input
              id="farm-lat"
              type="number"
              inputMode="decimal"
              step="any"
              value={form.latitude}
              onChange={(e) => handleChange('latitude', e.target.value)}
              placeholder={t('farm.latitudePlaceholder')}
              aria-label={t('farm.latitude')}
            />
          </div>

          {/* Longitude */}
          <div>
            <label
              htmlFor="farm-lng"
              className="block text-base font-medium text-gray-700 mb-2"
            >
              {t('farm.longitude')}
            </label>
            <input
              id="farm-lng"
              type="number"
              inputMode="decimal"
              step="any"
              value={form.longitude}
              onChange={(e) => handleChange('longitude', e.target.value)}
              placeholder={t('farm.longitudePlaceholder')}
              aria-label={t('farm.longitude')}
            />
          </div>

          {/* Buttons */}
          <div className="space-y-3 pt-2">
            <button
              type="submit"
              className="btn-primary"
              disabled={loading || !form.name.trim()}
              aria-label={t('farm.save')}
            >
              {loading ? t('common.loading') : t('farm.save')}
            </button>

            <button
              type="button"
              onClick={() => navigate('/farms')}
              className="btn-secondary"
              aria-label={t('farm.cancel')}
            >
              {t('farm.cancel')}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
