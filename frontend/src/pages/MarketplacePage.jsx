import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  IoArrowBack,
  IoPricetagOutline,
  IoStorefrontOutline,
  IoAddCircleOutline,
  IoReceiptOutline,
  IoSearchOutline,
  IoCallOutline,
  IoCheckmarkCircle,
  IoShieldCheckmark,
  IoStar,
  IoTrendingUp,
  IoTrendingDown,
} from 'react-icons/io5';
import api from '../api/axios';

export default function MarketplacePage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('mandi'); // mandi, browse, create, offers
  const [prices, setPrices] = useState([]);
  const [listings, setListings] = useState([]);
  const [offers, setOffers] = useState({ received_offers: [], made_offers: [] });
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // Create Listing form state
  const [listingForm, setListingForm] = useState({
    crop: 'Soybean',
    quantity_quintals: '',
    quality_grade: 'Grade A (Premium)',
    expected_price: '',
    location: '',
  });
  const [priceComparison, setPriceComparison] = useState(null);

  // Offer modal state
  const [selectedListingForOffer, setSelectedListingForOffer] = useState(null);
  const [offerForm, setOfferForm] = useState({ offered_price: '', quantity: '' });

  useEffect(() => {
    loadMandiPrices();
    loadListings();
    loadOffers();
  }, []);

  const loadMandiPrices = async () => {
    try {
      const res = await api.get('/marketplace/prices');
      setPrices(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadListings = async () => {
    try {
      const res = await api.get('/marketplace/listings');
      setListings(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadOffers = async () => {
    try {
      const res = await api.get('/marketplace/offers');
      setOffers(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  // Real-time price check against mandi modal average
  const checkPriceAgainstMandi = async (crop, price) => {
    if (!crop || !price || isNaN(price)) return;
    try {
      const res = await api.post('/marketplace/compare-price', {
        crop,
        expected_price: parseFloat(price),
      });
      setPriceComparison(res.data);
    } catch (err) {
      setPriceComparison(null);
    }
  };

  const handlePriceChange = (val) => {
    setListingForm({ ...listingForm, expected_price: val });
    if (val && parseFloat(val) > 0) {
      checkPriceAgainstMandi(listingForm.crop, val);
    } else {
      setPriceComparison(null);
    }
  };

  const handleCreateListing = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      await api.post('/marketplace/listings', {
        crop: listingForm.crop,
        quantity_quintals: parseFloat(listingForm.quantity_quintals),
        quality_grade: listingForm.quality_grade,
        expected_price: parseFloat(listingForm.expected_price),
        location: listingForm.location,
      });
      setMessage('✅ Listing published successfully!');
      setListingForm({
        crop: 'Soybean',
        quantity_quintals: '',
        quality_grade: 'Grade A (Premium)',
        expected_price: '',
        location: '',
      });
      setPriceComparison(null);
      await loadListings();
      setActiveTab('browse');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create listing');
    } finally {
      setSubmitting(false);
    }
  };

  const handleMakeOffer = async (e) => {
    e.preventDefault();
    if (!selectedListingForOffer) return;
    setSubmitting(true);
    try {
      await api.post(`/marketplace/listings/${selectedListingForOffer.id}/offer`, {
        offered_price: parseFloat(offerForm.offered_price),
        quantity: parseFloat(offerForm.quantity),
      });
      alert('Offer submitted successfully to the farmer!');
      setSelectedListingForOffer(null);
      setOfferForm({ offered_price: '', quantity: '' });
      await loadOffers();
      setActiveTab('offers');
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to submit offer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateOfferStatus = async (offerId, newStatus) => {
    try {
      await api.put(`/marketplace/offers/${offerId}/status`, { status: newStatus });
      await loadOffers();
    } catch (err) {
      alert('Status update failed');
    }
  };

  const filteredPrices = prices.filter(
    (p) =>
      p.commodity.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.mandi_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.district.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
          <h1 className="text-2xl font-bold text-gray-900">{t('market.title')}</h1>
        </div>

        <button
          onClick={() => navigate('/admin')}
          className="text-xs font-bold text-gray-500 bg-gray-100 hover:bg-gray-200 px-2.5 py-1.5 rounded-lg"
        >
          Admin
        </button>
      </header>

      {/* 4 Tabs */}
      <div className="px-4 mt-3">
        <div className="grid grid-cols-4 gap-1 bg-gray-100 p-1 rounded-2xl text-xs font-semibold text-center">
          <button
            onClick={() => setActiveTab('mandi')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'mandi'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600'
            }`}
          >
            📈 {t('market.mandiTab')}
          </button>
          <button
            onClick={() => setActiveTab('browse')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'browse'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600'
            }`}
          >
            🛒 {t('market.browseTab')}
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'create'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600'
            }`}
          >
            ➕ {t('market.createTab')}
          </button>
          <button
            onClick={() => setActiveTab('offers')}
            className={`py-2 px-1 rounded-xl transition-all ${
              activeTab === 'offers'
                ? 'bg-white text-green-700 shadow-sm font-bold'
                : 'text-gray-600'
            }`}
          >
            🤝 {t('market.offersTab')}
          </button>
        </div>
      </div>

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
            TAB 1: MANDI PRICES LIST
           ────────────────────────────────────────────── */}
        {activeTab === 'mandi' && (
          <div className="space-y-3">
            {/* Search Input */}
            <div className="relative">
              <IoSearchOutline className="w-5 h-5 absolute left-3.5 top-3.5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('market.searchCrop')}
                className="pl-11 pr-4 py-2.5 text-sm rounded-xl border border-gray-300"
              />
            </div>

            <div className="space-y-2.5">
              {filteredPrices.map((p) => (
                <div
                  key={p.id}
                  className="card bg-white border border-gray-200 p-3.5 rounded-xl shadow-xs"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[11px] font-bold text-green-800 bg-green-50 px-2 py-0.5 rounded-full">
                        🏛️ {p.mandi_name} ({p.district})
                      </span>
                      <h3 className="text-base font-bold text-gray-900 mt-1">
                        {p.commodity}
                      </h3>
                      <p className="text-xs text-gray-400 mt-0.5">
                        Arrival Date: {p.arrival_date}
                      </p>
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-gray-500 block">Modal Rate</span>
                      <span className="text-lg font-extrabold text-green-700">
                        ₹{p.modal_price}
                      </span>
                      <span className="text-[10px] text-gray-400 block">
                        / quintal
                      </span>
                    </div>
                  </div>

                  <div className="mt-2.5 pt-2 border-t border-gray-100 flex justify-between text-xs text-gray-600">
                    <span>Min: ₹{p.min_price}</span>
                    <span>Max: ₹{p.max_price}</span>
                    <span className="text-blue-600 font-semibold cursor-pointer"
                          onClick={() => {
                            setListingForm({ ...listingForm, crop: p.commodity.split(' ')[0], expected_price: p.modal_price.toString() });
                            setActiveTab('create');
                          }}>
                      Sell This ➔
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ──────────────────────────────────────────────
            TAB 2: DIRECT MARKETPLACE LISTINGS
           ────────────────────────────────────────────── */}
        {activeTab === 'browse' && (
          <div className="space-y-3">
            {/* Labeled Logistics Stub */}
            <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-xl text-blue-900 text-xs font-semibold flex items-center justify-between">
              <span>{t('market.logisticsStub')}</span>
              <span className="bg-blue-200 text-blue-950 px-2 py-0.5 rounded text-[10px]">
                Stub
              </span>
            </div>

            {listings.length === 0 ? (
              <div className="text-center py-12 card border-dashed">
                <IoStorefrontOutline className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm font-semibold text-gray-600">
                  No crop listings found.
                </p>
                <button
                  onClick={() => setActiveTab('create')}
                  className="btn-primary mt-3 max-w-xs mx-auto text-sm"
                >
                  List Your Harvest Now
                </button>
              </div>
            ) : (
              listings.map((l) => (
                <div
                  key={l.id}
                  className="card bg-white border border-gray-200 p-4 rounded-2xl shadow-xs space-y-2.5"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-[11px] font-bold bg-amber-100 text-amber-900 px-2.5 py-0.5 rounded-full">
                        {l.quality_grade}
                      </span>
                      <h3 className="text-lg font-bold text-gray-900 mt-1">
                        {l.crop}
                      </h3>
                      <p className="text-xs text-gray-500">📍 {l.location}</p>
                    </div>

                    <div className="text-right">
                      <span className="text-xl font-black text-green-700">
                        ₹{l.expected_price}
                      </span>
                      <span className="text-xs text-gray-400 block">/ quintal</span>
                    </div>
                  </div>

                  <div className="bg-gray-50 p-2 rounded-xl flex items-center justify-between text-xs text-gray-700">
                    <span>
                      📦 Available: <strong>{l.quantity_quintals} Quintals</strong>
                    </span>
                    <span>👤 {l.farmer_name}</span>
                  </div>

                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => {
                        setSelectedListingForOffer(l);
                        setOfferForm({ offered_price: l.expected_price.toString(), quantity: l.quantity_quintals.toString() });
                      }}
                      className="flex-1 btn-primary py-2 text-sm"
                    >
                      🤝 {t('market.makeOffer')}
                    </button>
                    {l.farmer_phone && (
                      <a
                        href={`tel:${l.farmer_phone}`}
                        className="p-2.5 bg-green-100 text-green-800 rounded-xl hover:bg-green-200 active:scale-95"
                      >
                        <IoCallOutline className="w-5 h-5" />
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* ──────────────────────────────────────────────
            TAB 3: CREATE DIRECT LISTING
           ────────────────────────────────────────────── */}
        {activeTab === 'create' && (
          <form onSubmit={handleCreateListing} className="card space-y-4">
            <h2 className="text-base font-bold text-gray-900 border-b pb-2">
              ➕ {t('market.createTab')}
            </h2>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('market.crop')}
              </label>
              <input
                type="text"
                value={listingForm.crop}
                onChange={(e) => {
                  setListingForm({ ...listingForm, crop: e.target.value });
                  if (listingForm.expected_price) {
                    checkPriceAgainstMandi(e.target.value, listingForm.expected_price);
                  }
                }}
                placeholder="e.g. Soybean, Cotton, Onion"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('market.quantity')}
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  value={listingForm.quantity_quintals}
                  onChange={(e) =>
                    setListingForm({
                      ...listingForm,
                      quantity_quintals: e.target.value,
                    })
                  }
                  placeholder="e.g. 25"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('market.grade')}
                </label>
                <select
                  value={listingForm.quality_grade}
                  onChange={(e) =>
                    setListingForm({
                      ...listingForm,
                      quality_grade: e.target.value,
                    })
                  }
                >
                  <option value="Grade A (Premium)">Grade A (Premium)</option>
                  <option value="Grade B (Standard)">Grade B (Standard)</option>
                  <option value="Grade C">Grade C</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('market.expectedPrice')}
              </label>
              <input
                type="number"
                step="10"
                min="100"
                value={listingForm.expected_price}
                onChange={(e) => handlePriceChange(e.target.value)}
                placeholder="e.g. 4800"
                required
              />
            </div>

            {/* Price vs Mandi comparison indicator */}
            {priceComparison && (
              <div
                className={`p-3 rounded-xl border text-xs font-semibold ${
                  priceComparison.indicator === 'fair'
                    ? 'bg-green-50 border-green-200 text-green-900'
                    : priceComparison.indicator === 'below'
                    ? 'bg-blue-50 border-blue-200 text-blue-900'
                    : 'bg-amber-50 border-amber-200 text-amber-900'
                }`}
              >
                <div className="flex items-center gap-1.5 mb-1 font-bold">
                  {priceComparison.indicator === 'fair' ? (
                    <IoCheckmarkCircle className="w-4 h-4 text-green-600" />
                  ) : priceComparison.indicator === 'below' ? (
                    <IoTrendingDown className="w-4 h-4 text-blue-600" />
                  ) : (
                    <IoTrendingUp className="w-4 h-4 text-amber-600" />
                  )}
                  <span>
                    {priceComparison.indicator === 'fair'
                      ? t('market.fair')
                      : priceComparison.indicator === 'below'
                      ? t('market.below')
                      : t('market.above')}
                  </span>
                </div>
                <p className="font-normal opacity-90 leading-relaxed">
                  {priceComparison[`advice_${i18n.language}`] ||
                    priceComparison.advice_en}
                </p>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('market.location')}
              </label>
              <input
                type="text"
                value={listingForm.location}
                onChange={(e) =>
                  setListingForm({ ...listingForm, location: e.target.value })
                }
                placeholder="Village, Taluka, District"
                required
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !listingForm.expected_price}
              className="btn-primary"
            >
              {submitting ? t('common.loading') : t('market.postListing')}
            </button>
          </form>
        )}

        {/* ──────────────────────────────────────────────
            TAB 4: OFFERS & DEALS WORKFLOW
           ────────────────────────────────────────────── */}
        {activeTab === 'offers' && (
          <div className="space-y-4">
            {/* Labeled UPI Sandbox Stub */}
            <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs font-semibold flex items-center justify-between">
              <span>{t('market.upiStub')}</span>
              <span className="bg-amber-200 text-amber-950 px-2 py-0.5 rounded text-[10px]">
                Stub
              </span>
            </div>

            {/* Received Offers */}
            <div>
              <h3 className="text-sm font-bold text-gray-900 mb-2">
                📥 Received Offers (On Your Listings)
              </h3>
              {offers.received_offers?.length === 0 ? (
                <p className="text-xs text-gray-400 card text-center py-4">
                  No offers received yet.
                </p>
              ) : (
                offers.received_offers.map((off) => (
                  <div
                    key={off.id}
                    className="card p-3.5 bg-white border border-gray-200 rounded-xl space-y-2 mb-2"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs font-bold text-gray-900">
                          {off.crop}
                        </span>
                        <p className="text-xs text-gray-500">
                          Buyer: {off.buyer_name}{' '}
                          {off.buyer_is_verified && (
                            <span className="text-green-700 font-bold">
                              ✓ Verified
                            </span>
                          )}
                        </p>
                      </div>
                      <span className="text-base font-extrabold text-green-700">
                        ₹{off.offered_price}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1 border-t">
                      <span className="font-semibold text-gray-600">
                        Status: <span className="uppercase text-green-800 font-bold">{off.status}</span>
                      </span>

                      {off.status === 'offer_made' && (
                        <button
                          onClick={() => handleUpdateOfferStatus(off.id, 'confirmed')}
                          className="bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-lg"
                        >
                          {t('market.confirm')}
                        </button>
                      )}
                      {off.status === 'confirmed' && (
                        <button
                          onClick={() => handleUpdateOfferStatus(off.id, 'delivered')}
                          className="bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-lg"
                        >
                          {t('market.deliver')}
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Modal: Submit Offer */}
        {selectedListingForOffer && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl p-5 max-w-sm w-full space-y-4 shadow-2xl">
              <h3 className="text-base font-bold text-gray-900 border-b pb-2">
                Make Offer for {selectedListingForOffer.crop}
              </h3>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Offered Price (Rs / Quintal)
                </label>
                <input
                  type="number"
                  value={offerForm.offered_price}
                  onChange={(e) =>
                    setOfferForm({ ...offerForm, offered_price: e.target.value })
                  }
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Quantity Required (Quintals)
                </label>
                <input
                  type="number"
                  value={offerForm.quantity}
                  onChange={(e) =>
                    setOfferForm({ ...offerForm, quantity: e.target.value })
                  }
                  required
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedListingForOffer(null)}
                  className="btn-secondary py-2 text-sm flex-1"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="button"
                  onClick={handleMakeOffer}
                  disabled={submitting}
                  className="btn-primary py-2 text-sm flex-1"
                >
                  {submitting ? t('common.loading') : 'Submit Offer'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

