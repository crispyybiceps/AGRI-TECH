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

  const [step, setStep] = useState(1); // 1 = phone, 2 = OTP
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [mockOtpHint, setMockOtpHint] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendOtp = async (e) => {
    e.preventDefault();
    if (!phone || phone.length < 10) return;

    setLoading(true);
    setError('');

    try {
      const res = await api.post('/auth/send-otp', { phone: `+91${phone}` });
      if (res.data?.mock_otp) {
        setMockOtpHint(res.data.mock_otp);
        setOtp(res.data.mock_otp); // Auto-fill for developer convenience
      }
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otp || otp.length < 6) return;

    setLoading(true);
    setError('');

    try {
      const res = await api.post('/auth/verify-otp', {
        phone: `+91${phone}`,
        otp,
      });
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
      <div className="pt-4 px-4">
        <LanguageSwitcher />
      </div>

      {/* Main content centered */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 pb-8">
        {/* App icon / branding */}
        <div className="text-center mb-8">
          <div className="text-7xl mb-3" aria-hidden="true">🌾</div>
          <h1 className="text-3xl font-bold text-green-700">{t('appName')}</h1>
          <p className="text-gray-500 mt-1 text-base">{t('login.title')}</p>
        </div>

        {/* Error message */}
        {error && (
          <div
            className="w-full bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-4 text-center"
            role="alert"
          >
            {error}
          </div>
        )}

        {step === 1 ? (
          /* Step 1: Phone number */
          <form onSubmit={handleSendOtp} className="w-full space-y-4">
            <div>
              <label
                htmlFor="phone"
                className="block text-base font-medium text-gray-700 mb-2"
              >
                {t('login.phoneNumber')}
              </label>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-gray-600 bg-gray-100 px-3 py-3 rounded-lg border border-gray-300">
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
                  className="flex-1"
                  aria-label={t('login.enterPhone')}
                  autoComplete="tel-national"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary mt-2"
              disabled={loading || phone.length < 10}
              aria-label={t('login.sendOtp')}
            >
              {loading ? t('common.loading') : t('login.sendOtp')}
            </button>
          </form>
        ) : (
          /* Step 2: OTP verification */
          <form onSubmit={handleVerifyOtp} className="w-full space-y-4">
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-center mb-2">
              {t('login.otpSent')}
              {mockOtpHint && (
                <div className="mt-2 p-2 bg-amber-50 border border-amber-300 rounded-lg text-amber-900 text-sm font-semibold">
                  ⚡ Dev Mode Mock OTP: <span className="font-mono text-lg font-bold text-green-800 tracking-widest">{mockOtpHint}</span>
                  <div className="text-[11px] text-gray-500 font-normal mt-0.5">(Auto-filled below for testing)</div>
                </div>
              )}
            </div>

            <div>
              <label
                htmlFor="otp"
                className="block text-base font-medium text-gray-700 mb-2"
              >
                {t('login.enterOtp')}
              </label>
              <input
                id="otp"
                type="tel"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                placeholder={t('login.otpPlaceholder')}
                className="text-center text-2xl tracking-[0.5em] font-mono"
                aria-label={t('login.enterOtp')}
                autoComplete="one-time-code"
                required
              />
            </div>

            <button
              type="submit"
              className="btn-primary mt-2"
              disabled={loading || otp.length < 6}
              aria-label={t('login.verify')}
            >
              {loading ? t('common.loading') : t('login.verify')}
            </button>

            <button
              type="button"
              onClick={() => {
                setStep(1);
                setOtp('');
                setError('');
              }}
              className="btn-secondary"
              aria-label={t('common.back')}
            >
              {t('common.back')}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
