import { useTranslation } from 'react-i18next';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const languages = [
    { code: 'mr', label: 'मराठी' },
    { code: 'hi', label: 'हिंदी' },
    { code: 'en', label: 'English' },
  ];

  const switchLanguage = (langCode) => {
    i18n.changeLanguage(langCode);
    localStorage.setItem('agritech_lang', langCode);
  };

  return (
    <div className="flex gap-2 justify-center" role="group" aria-label="Language selection">
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => switchLanguage(lang.code)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors duration-150 ${
            i18n.language === lang.code
              ? 'bg-green-600 text-white shadow-md'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
          aria-label={`Switch language to ${lang.label}`}
          aria-pressed={i18n.language === lang.code}
        >
          {lang.label}
        </button>
      ))}
    </div>
  );
}
