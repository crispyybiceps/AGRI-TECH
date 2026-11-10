import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LanguageSwitcher from '../components/LanguageSwitcher';
import api from '../api/axios';

export default function ProfilePage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user, updateUser, logout } = useAuth();

  const [name, setName] = useState(user?.name || '');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const res = await api.put('/profile', {
        name,
        language_preference: i18n.language,
      });
      updateUser(res.data);
      setMessage(t('profile.saved'));
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app-container pb-20">
      <header className="px-4 pt-4">
        <h1 className="text-2xl font-bold text-gray-900">{t('profile.title')}</h1>
      </header>

      <main className="px-4 mt-6">
        <form onSubmit={handleSave} className="space-y-5">
          {/* Success message */}
          {message && (
            <div
              className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-center"
              role="status"
            >
              {message}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div
              className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-center"
              role="alert"
            >
              {error}
            </div>
          )}

          {/* Phone (read-only) */}
          <div>
            <label className="block text-base font-medium text-gray-700 mb-2">
              {t('profile.phone')}
            </label>
            <input
              type="tel"
              value={user?.phone || ''}
              readOnly
              className="bg-gray-100 text-gray-500 cursor-not-allowed"
              aria-label={t('profile.phone')}
            />
          </div>

          {/* Name */}
          <div>
            <label
              htmlFor="profile-name"
              className="block text-base font-medium text-gray-700 mb-2"
            >
              {t('profile.name')}
            </label>
            <input
              id="profile-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('profile.namePlaceholder')}
              aria-label={t('profile.name')}
            />
          </div>

          {/* Language */}
          <div>
            <label className="block text-base font-medium text-gray-700 mb-2">
              {t('profile.language')}
            </label>
            <LanguageSwitcher />
          </div>

          {/* Save button */}
          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            aria-label={t('profile.save')}
          >
            {loading ? t('common.loading') : t('profile.save')}
          </button>
        </form>

        {/* Logout */}
        <div className="mt-8">
          <button
            onClick={handleLogout}
            className="btn-danger"
            aria-label={t('profile.logout')}
          >
            {t('profile.logout')}
          </button>
        </div>
      </main>
    </div>
  );
}
