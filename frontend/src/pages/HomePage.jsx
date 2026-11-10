import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { IoChatbubblesOutline, IoCloudOutline } from 'react-icons/io5';
import { PiPlant } from 'react-icons/pi';
import { IoPricetagsOutline } from 'react-icons/io5';

export default function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleAction = (featureId) => {
    if (featureId === 'weather') {
      navigate('/weather');
    } else if (featureId === 'soil') {
      navigate('/soil');
    } else if (featureId === 'expert') {
      navigate('/chat');
    } else if (featureId === 'prices') {
      navigate('/marketplace');
    } else {
      alert(t('common.comingSoon'));
    }
  };

  const buttons = [
    {
      id: 'expert',
      label: t('homeScreen.askExpert'),
      icon: IoChatbubblesOutline,
      emoji: '💬',
      bgColor: 'bg-green-500',
      hoverColor: 'hover:bg-green-600',
      activeColor: 'active:bg-green-700',
    },
    {
      id: 'weather',
      label: t('homeScreen.weather'),
      icon: IoCloudOutline,
      emoji: '🌤️',
      bgColor: 'bg-blue-500',
      hoverColor: 'hover:bg-blue-600',
      activeColor: 'active:bg-blue-700',
    },
    {
      id: 'soil',
      label: t('homeScreen.mySoil'),
      icon: PiPlant,
      emoji: '🌱',
      bgColor: 'bg-amber-600',
      hoverColor: 'hover:bg-amber-700',
      activeColor: 'active:bg-amber-800',
    },
    {
      id: 'prices',
      label: t('homeScreen.sellPrices'),
      icon: IoPricetagsOutline,
      emoji: '💰',
      bgColor: 'bg-orange-500',
      hoverColor: 'hover:bg-orange-600',
      activeColor: 'active:bg-orange-700',
    },
  ];

  return (
    <div className="app-container pb-20">
      {/* Header */}
      <header className="px-4 pt-4 pb-2">
        <LanguageSwitcher />
        <div className="mt-4">
          <h1 className="text-2xl font-bold text-gray-900">
            {t('homeScreen.greeting')}
            {user?.name ? `, ${user.name}` : ''} 👋
          </h1>
          <p className="text-base text-gray-500 mt-1">{t('appName')}</p>
        </div>
      </header>

      {/* 2x2 Grid of action buttons */}
      <main className="px-4 mt-6">
        <div className="grid grid-cols-2 gap-4" role="group" aria-label="Main actions">
          {buttons.map((btn) => (
            <button
              key={btn.id}
              onClick={() => handleAction(btn.id)}
              className={`${btn.bgColor} ${btn.hoverColor} ${btn.activeColor} 
                text-white rounded-2xl p-4 flex flex-col items-center justify-center 
                min-h-[140px] shadow-lg transition-all duration-150 
                active:scale-95 focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-green-300`}
              aria-label={btn.label}
            >
              <span className="text-5xl mb-3" aria-hidden="true">
                {btn.emoji}
              </span>
              <span className="text-lg font-semibold leading-tight text-center">
                {btn.label}
              </span>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
