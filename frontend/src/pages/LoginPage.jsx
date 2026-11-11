import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import LanguageSwitcher from '../components/LanguageSwitcher';
import api from '../api/axios';

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();

  const [isSignup, setIsSignup] = useState(false);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!phone || phone.length < 10) return;
    if (!password) return;

    setLoading(true);
    setError('');

    const formattedPhone = phone.startsWith('+') ? phone : `+91${phone}`;

    try {
      let res;
      if (isSignup) {
        res = await api.post('/auth/signup', {
          phone: formattedPhone,
          password,
          name: name.trim() || undefined,
        });
      } else {
        res = await api.post('/auth/login', {
          phone: formattedPhone,
          password,
        });
      }

      const { access_token, user } = res.data;
      login(access_token, user);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container flex flex-col min-h-screen">
      {/* Language switcher at top */}
      <div className="pt-4 px-4 flex justify-end">
        <LanguageSwitcher />
      </div>

      {/* Main content centered */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 pb-8">
        {/* App branding */}
        <div className="text-center mb-6">
          <div className="text-6xl mb-2" aria-hidden="true">🌾</div>
          <h1 className="text-3xl font-bold text-green-700">{t('appName')}</h1>
          <p className="text-gray-500 mt-1 text-sm">{t('login.title')}</p>
        </div>

        {/* Tab switcher: Login / Sign Up */}
        <div className="w-full flex bg-gray-100 p-1 rounded-xl mb-6 border border-gray-200">
          <button
            type="button"
            onClick={() => {
              setIsSignup(false);
              setError('');
            }}
            className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all ${
              !isSignup
                ? 'bg-white text-green-800 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {t('login.loginTab')}
          </button>
          <button
            type="button"
            onClick={() => {
              setIsSignup(true);
              setError('');
            }}
            className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all ${
              isSignup
                ? 'bg-white text-green-800 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {t('login.signupTab')}
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div
            className="w-full bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-4 text-center text-sm"
            role="alert"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="w-full space-y-4">
          {/* Full Name (Sign Up only) */}
          {isSignup && (
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {t('login.name')}
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('login.enterName')}
                className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-600 focus:border-transparent text-base"
                autoComplete="name"
              />
            </div>
          )}

          {/* Phone Number */}
          <div>
            <label
              htmlFor="phone"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {t('login.phoneNumber')}
            </label>
            <div className="flex items-center gap-2">
              <span className="text-base font-semibold text-gray-600 bg-gray-100 px-3 py-3 rounded-xl border border-gray-300">
                +91
              </span>
              <input
                id="phone"
                type="tel"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={10}
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                placeholder={t('login.enterPhone')}
                className="flex-1 px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-600 focus:border-transparent text-base"
                autoComplete="tel-national"
                required
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {t('login.password')}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t('login.enterPassword')}
              className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-green-600 focus:border-transparent text-base"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              required
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="w-full bg-green-700 hover:bg-green-800 text-white font-semibold py-3.5 px-4 rounded-xl shadow-md transition-colors mt-2 text-base disabled:opacity-50"
            disabled={loading || phone.length < 10 || !password}
          >
            {loading ? t('common.loading') : isSignup ? t('login.signupBtn') : t('login.loginBtn')}
          </button>

          {/* Toggle between Login and Sign Up */}
          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => {
                setIsSignup(!isSignup);
                setError('');
              }}
              className="text-sm text-green-700 hover:text-green-800 font-medium"
            >
              {isSignup ? t('login.alreadyHaveAccount') : t('login.dontHaveAccount')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
