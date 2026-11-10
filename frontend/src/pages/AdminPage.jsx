import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  IoArrowBack,
  IoShieldCheckmarkOutline,
  IoFlagOutline,
  IoDocumentTextOutline,
  IoCheckmarkCircle,
  IoStatsChartOutline,
} from 'react-icons/io5';
import api from '../api/axios';

export default function AdminPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [analytics, setAnalytics] = useState(null);
  const [flaggedChats, setFlaggedChats] = useState([]);
  const [knowledgeDocs, setKnowledgeDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadAdminData();
  }, []);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [aRes, fRes, kRes] = await Promise.all([
        api.get('/admin/analytics'),
        api.get('/chat/flagged'),
        api.get('/admin/knowledge'),
      ]);
      setAnalytics(aRes.data);
      setFlaggedChats(fRes.data);
      setKnowledgeDocs(kRes.data);
      if (kRes.data.length > 0) {
        setSelectedDoc(kRes.data[0]);
        setEditContent(kRes.data[0].content);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDoc = async () => {
    if (!selectedDoc) return;
    setSaving(true);
    setMessage('');
    try {
      await api.put(`/admin/knowledge/${selectedDoc.filename}`, {
        content: editContent,
      });
      setMessage(`✅ Updated ${selectedDoc.filename} successfully!`);
    } catch (err) {
      alert('Failed to save document.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="app-container pb-24">
      <header className="px-4 pt-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="p-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label={t('common.back')}
          >
            <IoArrowBack className="w-6 h-6" />
          </button>
          <h1 className="text-xl font-bold text-gray-900">{t('admin.title')}</h1>
        </div>
      </header>

      <main className="px-4 mt-4 space-y-4">
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-10 h-10 border-4 border-green-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* Analytics Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="card p-3 bg-green-50 border-green-200">
                <span className="text-xs text-green-800 font-semibold">
                  {t('admin.users')}
                </span>
                <p className="text-2xl font-black text-green-950 mt-1">
                  {analytics?.users?.total ?? 0}
                </p>
                <span className="text-[10px] text-green-700">
                  {analytics?.users?.farmers} Farmers • {analytics?.users?.buyers} Buyers
                </span>
              </div>

              <div className="card p-3 bg-blue-50 border-blue-200">
                <span className="text-xs text-blue-800 font-semibold">
                  {t('admin.listings')}
                </span>
                <p className="text-2xl font-black text-blue-950 mt-1">
                  {analytics?.marketplace?.active_listings ?? 0}
                </p>
                <span className="text-[10px] text-blue-700">
                  {analytics?.marketplace?.total_offers} Offers Made
                </span>
              </div>

              <div className="card p-3 bg-indigo-50 border-indigo-200">
                <span className="text-xs text-indigo-800 font-semibold">
                  {t('admin.chats')}
                </span>
                <p className="text-2xl font-black text-indigo-950 mt-1">
                  {analytics?.chatbot?.total_sessions ?? 0}
                </p>
                <span className="text-[10px] text-indigo-700">Total Sessions</span>
              </div>

              <div className="card p-3 bg-red-50 border-red-200">
                <span className="text-xs text-red-800 font-semibold">
                  {t('admin.flagged')}
                </span>
                <p className="text-2xl font-black text-red-950 mt-1">
                  {analytics?.chatbot?.flagged_answers ?? 0}
                </p>
                <span className="text-[10px] text-red-700">Pending Review</span>
              </div>
            </div>

            {/* Flagged Answers Review Queue */}
            <div className="card space-y-3">
              <div className="flex items-center justify-between border-b pb-2">
                <h2 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
                  <IoFlagOutline className="text-red-600" />
                  Flagged Answers Quality Queue
                </h2>
                <span className="text-xs font-bold bg-red-100 text-red-800 px-2 py-0.5 rounded-full">
                  {flaggedChats.length}
                </span>
              </div>

              {flaggedChats.length === 0 ? (
                <p className="text-xs text-gray-400 py-3 text-center">
                  No flagged answers pending review.
                </p>
              ) : (
                <div className="space-y-2">
                  {flaggedChats.map((c) => (
                    <div
                      key={c.id}
                      className="p-3 bg-red-50/60 border border-red-200 rounded-xl text-xs space-y-1.5"
                    >
                      <div className="flex justify-between font-bold text-red-900">
                        <span>Message #{c.id}</span>
                        <span>Reason: {c.flag_reason}</span>
                      </div>
                      <p className="text-gray-800 bg-white p-2 rounded border border-red-100">
                        {c.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Knowledge Base Editor */}
            <div className="card space-y-3">
              <div className="flex items-center justify-between border-b pb-2">
                <h2 className="text-sm font-bold text-gray-900 flex items-center gap-1.5">
                  <IoDocumentTextOutline className="text-green-600" />
                  {t('admin.knowledgeBase')}
                </h2>
              </div>

              {message && (
                <div className="p-2 bg-green-50 border border-green-200 text-green-800 text-xs rounded-lg">
                  {message}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Select Document to Edit:
                </label>
                <select
                  value={selectedDoc?.filename || ''}
                  onChange={(e) => {
                    const doc = knowledgeDocs.find((d) => d.filename === e.target.value);
                    setSelectedDoc(doc);
                    setEditContent(doc?.content || '');
                  }}
                  className="text-xs font-semibold"
                >
                  {knowledgeDocs.map((doc) => (
                    <option key={doc.filename} value={doc.filename}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <textarea
                  rows={8}
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="text-xs font-mono p-2.5 rounded-xl border border-gray-300 w-full"
                />
              </div>

              <button
                onClick={handleSaveDoc}
                disabled={saving}
                className="btn-primary py-2 text-xs"
              >
                {saving ? t('common.loading') : 'Save Knowledge Document'}
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

