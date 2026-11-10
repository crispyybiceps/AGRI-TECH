import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { IoHomeOutline, IoHome } from 'react-icons/io5';
import { PiPlant, PiPlantFill } from 'react-icons/pi';
import { IoPersonOutline, IoPerson } from 'react-icons/io5';

export default function BottomNav() {
  const { t } = useTranslation();

  const navItems = [
    {
      to: '/',
      label: t('nav.home'),
      icon: IoHomeOutline,
      activeIcon: IoHome,
    },
    {
      to: '/farms',
      label: t('nav.farms'),
      icon: PiPlant,
      activeIcon: PiPlantFill,
    },
    {
      to: '/profile',
      label: t('nav.profile'),
      icon: IoPersonOutline,
      activeIcon: IoPerson,
    },
  ];

  return (
    <nav
      className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] bg-white border-t border-gray-200 z-50"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="flex justify-around items-center h-16">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-0.5 px-4 py-1 rounded-lg transition-colors ${
                isActive
                  ? 'text-green-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`
            }
            aria-label={item.label}
          >
            {({ isActive }) => (
              <>
                {isActive ? (
                  <item.activeIcon className="w-6 h-6" aria-hidden="true" />
                ) : (
                  <item.icon className="w-6 h-6" aria-hidden="true" />
                )}
                <span className="text-xs font-medium">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
