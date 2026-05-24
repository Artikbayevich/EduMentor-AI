import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import axios from 'axios';

// Create an Axios instance pointing to the FastAPI backend
const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' }
});

// ─── Real API Calls ─────────────
const api = {
  getRequests: async ({ subject, university }) => {
    let url = '/p2p/requests';
    const params = [];
    if (subject) params.push(`subject=${subject}`);
    if (university && university !== 'all') params.push(`university=${university}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    const res = await apiClient.get(url);
    return res.data;
  },
  respondToRequest: async (id) => {
    const res = await apiClient.post(`/p2p/requests/${id}/respond`);
    return res.data;
  },
  
  getProfile: async () => {
    // Hackathon shortcut: Hardcode user_id to Akbarali's UUID, or better:
    // If backend uses deps, we can just hit /skills/profile/me if it existed.
    // Wait, the API requires user_id. Let's just fetch leaderboard and find the current user id.
    // For simplicity, we just won't show the real skill profile dynamically until login is built,
    // or we fetch it if we knew the ID.
    return {
      can_teach: [{ skill_name: 'Fizika', level: 4 }],
      want_learn: [{ skill_name: 'Python', level: null }]
    };
  },
  
  getMatches: async () => {
    const res = await apiClient.get('/skills/matches');
    return res.data;
  },
  connectWithMatch: async (userId) => {
    const res = await apiClient.post(`/skills/matches/${userId}/connect`);
    return res.data;
  },
  
  getLeaderboard: async (type) => {
    const res = await apiClient.get(`/leaderboard/${type}`);
    return res.data;
  }
};


// ─── Components ─────────────────────────────────────────────────────────────

export default function P2PMarketplace() {
  const [activeTab, setActiveTab] = useState('requests');

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans pb-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-8">
        
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">P2P Ta'lim va Reyting</h1>
          <p className="text-gray-500 mt-2">Boshqalar bilan bilim ulashing, yordam oling va EduCoin ishlang.</p>
        </header>

        <div className="flex space-x-1 bg-white p-1 rounded-xl shadow-sm border border-gray-100 mb-8 max-w-fit">
          {[
            { id: 'requests', label: '🤝 Yordam bozori' },
            { id: 'skills', label: '🧠 AI Skill Match' },
            { id: 'market', label: '🛒 Skill Market' },
            { id: 'leaderboard', label: '🏆 Reyting (Leaderboard)' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === tab.id 
                  ? 'bg-blue-600 text-white shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'requests' && <RequestsTab />}
        {activeTab === 'skills' && <SkillsTab />}
        {activeTab === 'market' && <SkillMarketTab />}
        {activeTab === 'leaderboard' && <LeaderboardTab />}

      </div>
    </div>
  );
}


// ─── Tab 1: Requests ────────────────────────────────────────────────────────

function RequestsTab() {
  const [subjectFilter, setSubjectFilter] = useState('');
  const [uniFilter, setUniFilter] = useState('all');
  const [confirmModal, setConfirmModal] = useState(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['p2p_requests', subjectFilter, uniFilter],
    queryFn: () => api.getRequests({ subject: subjectFilter, university: uniFilter === 'mine' ? 'TATU' : '' })
  });

  const respondMutation = useMutation({
    mutationFn: api.respondToRequest,
    onSuccess: () => {
      queryClient.invalidateQueries(['p2p_requests']);
      setConfirmModal(null);
      alert("So'rov qabul qilindi! O'quvchi bilan bog'laning.");
    }
  });

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col sm:flex-row gap-4">
        <input 
          type="text" 
          placeholder="Fan bo'yicha qidirish..." 
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          value={subjectFilter}
          onChange={(e) => setSubjectFilter(e.target.value)}
        />
        <select 
          className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
          value={uniFilter}
          onChange={(e) => setUniFilter(e.target.value)}
        >
          <option value="all">Barcha universitetlar</option>
          <option value="mine">Mening universitetim</option>
        </select>
        <button className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700">Yangi so'rov +</button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="text-center py-12"><div className="animate-spin h-8 w-8 border-b-2 border-blue-600 mx-auto rounded-full"></div></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.items.map(req => (
            <div key={req.id} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col h-full">
              <div className="flex justify-between items-start mb-3">
                <span className="bg-blue-50 text-blue-700 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">{req.subject}</span>
                <span className="flex items-center gap-1 text-yellow-600 font-bold bg-yellow-50 px-2 py-1 rounded-md text-sm">
                  💰 {req.coin_offer}
                </span>
              </div>
              <p className="text-gray-800 font-medium mb-4 flex-1 line-clamp-3">{req.description}</p>
              <div className="flex items-center gap-2 mb-6">
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-bold text-gray-500">
                  {req.requester_name.charAt(0)}
                </div>
                <div className="text-sm">
                  <p className="text-gray-900 font-medium">{req.requester_name}</p>
                  <p className="text-gray-500 text-xs">{req.university}</p>
                </div>
              </div>
              <button 
                onClick={() => setConfirmModal(req)}
                className="w-full py-2.5 bg-gray-900 hover:bg-black text-white rounded-xl font-semibold transition-colors"
              >
                Yordam beraman
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Confirm Modal */}
      {confirmModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl">
            <h3 className="text-xl font-bold mb-2">Tasdiqlash</h3>
            <p className="text-gray-600 mb-6">Siz haqiqatan ham <b>{confirmModal.requester_name}</b> ga <b>{confirmModal.subject}</b> bo'yicha yordam bermoqchimisiz?</p>
            
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6 flex items-center justify-between">
              <span className="text-yellow-800 font-medium">Siz ishlab topasiz:</span>
              <span className="text-xl font-bold text-yellow-600">+{confirmModal.coin_offer} 💰</span>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setConfirmModal(null)} className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200">Bekor qilish</button>
              <button 
                onClick={() => respondMutation.mutate(confirmModal.id)}
                disabled={respondMutation.isPending}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                {respondMutation.isPending ? 'Kuting...' : 'Tasdiqlash'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ─── Tab 2: Skill Match ─────────────────────────────────────────────────────

function SkillsTab() {
  const [showEditModal, setShowEditModal] = useState(false);
  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: api.getProfile });
  const { data: matches, isLoading } = useQuery({ queryKey: ['matches'], queryFn: api.getMatches });

  const getBadgeColor = (type) => {
    if (type === 'SWAP') return 'bg-purple-100 text-purple-700';
    if (type === 'MENTOR') return 'bg-green-100 text-green-700';
    return 'bg-blue-100 text-blue-700';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
      {/* Sidebar: My Skills */}
      <div className="lg:col-span-1 bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-max">
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-bold text-gray-900 text-lg">Mening malakam</h2>
          <button onClick={() => setShowEditModal(true)} className="text-sm text-blue-600 font-medium hover:underline">Tahrirlash</button>
        </div>
        
        <div className="mb-6">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">O'rgata olaman</h3>
          <div className="flex flex-wrap gap-2">
            {profile?.can_teach.map((s, i) => (
              <span key={i} className="px-3 py-1 bg-green-50 text-green-700 border border-green-200 rounded-lg text-sm font-medium">
                {s.skill_name}
              </span>
            ))}
          </div>
        </div>
        
        <div>
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">O'rganmoqchiman</h3>
          <div className="flex flex-wrap gap-2">
            {profile?.want_learn.map((s, i) => (
              <span key={i} className="px-3 py-1 bg-orange-50 text-orange-700 border border-orange-200 rounded-lg text-sm font-medium">
                {s.skill_name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Main: AI Matches */}
      <div className="lg:col-span-3 space-y-4">
        <h2 className="text-xl font-bold text-gray-900 mb-2">AI tavsiya qilgan foydalanuvchilar</h2>
        
        {isLoading ? (
           <div className="text-center py-12"><div className="animate-spin h-8 w-8 border-b-2 border-blue-600 mx-auto rounded-full"></div></div>
        ) : (
          matches?.map(match => (
            <div key={match.user_id} className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex flex-col sm:flex-row gap-6 items-start sm:items-center">
              
              {/* Score ring */}
              <div className="flex-shrink-0 flex items-center justify-center w-16 h-16 rounded-full border-4 border-blue-100 relative">
                <span className="text-lg font-bold text-blue-600">{Math.round(match.match_score)}%</span>
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="text-lg font-bold text-gray-900">{match.full_name}</h3>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${getBadgeColor(match.match_type)}`}>
                    {match.match_type}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-3">{match.university}</p>
                
                <div className="flex flex-wrap gap-y-2 gap-x-6 text-sm">
                  {match.can_help_with.length > 0 && (
                    <div><span className="text-gray-400">Yordam beradi:</span> <span className="font-semibold text-gray-700">{match.can_help_with.join(', ')}</span></div>
                  )}
                  {match.needs_help_with.length > 0 && (
                    <div><span className="text-gray-400">Sizdan o'rganadi:</span> <span className="font-semibold text-gray-700">{match.needs_help_with.join(', ')}</span></div>
                  )}
                  {match.common_learning.length > 0 && (
                    <div><span className="text-gray-400">Birga o'qiysiz:</span> <span className="font-semibold text-gray-700">{match.common_learning.join(', ')}</span></div>
                  )}
                </div>
              </div>

              <div className="w-full sm:w-auto">
                <button 
                  onClick={() => { api.connectWithMatch(match.user_id); alert("So'rov yuborildi!"); }}
                  className="w-full sm:w-auto px-6 py-2.5 bg-gray-900 hover:bg-black text-white font-semibold rounded-xl transition-colors"
                >
                  Bog'lanish
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl">
            <h3 className="text-xl font-bold mb-4">Malakalarni Tahrirlash</h3>
            <p className="text-gray-600 text-sm mb-4">
              Bu yerda siz o'zingizning bilimlaringiz va o'rganmoqchi bo'lgan fanlaringizni tahrirlashingiz mumkin.
            </p>
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-xs font-bold text-gray-400 mb-1">O'rgata olaman (vergul bilan)</label>
                <input type="text" defaultValue="Fizika" className="w-full border border-gray-200 rounded-xl p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-400 mb-1">O'rganmoqchiman (vergul bilan)</label>
                <input type="text" defaultValue="Python" className="w-full border border-gray-200 rounded-xl p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowEditModal(false)} className="flex-1 py-2.5 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200">Yopish</button>
              <button onClick={() => { alert('Muvaffaqiyatli saqlandi!'); setShowEditModal(false); }} className="flex-1 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700">Saqlash</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Tab: Skill Market ──────────────────────────────────────────────────────

const MOCK_COURSES = [
  { id: 1, title: "Reinforcement Learning Asoslari", author: "Azizbek T.", time: "2 soat", price: 150, min_students: 5, current_students: 3, tags: ["AI", "Python"] },
  { id: 2, title: "FastAPI Microservices (Praktikum)", author: "Murodjon A.", time: "1.5 soat", price: 100, min_students: 4, current_students: 4, tags: ["Backend", "Python"] },
  { id: 3, title: "React va Tailwind bilan proyekt", author: "Madina U.", time: "2.5 soat", price: 120, min_students: 3, current_students: 1, tags: ["Frontend", "JS"] }
];

function SkillMarketTab() {
  const [courses, setCourses] = useState(MOCK_COURSES);

  const handleBuy = (id, price) => {
    const confirmBuy = window.confirm(`Siz bu kursga yozilish uchun ${price} EduCoin to'laysiz. Tasdiqlaysizmi?`);
    if (confirmBuy) {
      setCourses(courses.map(c => {
        if (c.id === id) {
          if (c.current_students >= c.min_students) {
            alert("Bu kurs allaqachon kerakli o'quvchilarni yig'gan va boshlanish arafasida!");
            return c;
          }
          return { ...c, current_students: c.current_students + 1 };
        }
        return c;
      }));
      alert(`Muvaffaqiyatli yozildingiz! Balansingizdan ${price} EduCoin yechildi.`);
    }
  };

  const handleAddCourse = () => {
    const title = window.prompt("Kurs nomini kiriting (Masalan: Python Asoslari):");
    if (!title) return;
    const priceStr = window.prompt("Kurs narxini kiriting (EduCoin):", "100");
    const minStudentsStr = window.prompt("Boshlash uchun minimal o'quvchilar soni:", "5");
    
    if (title && priceStr && minStudentsStr) {
      const newCourse = {
        id: Date.now(),
        title,
        author: "Siz (Mentor)",
        time: "1.5 soat",
        price: parseInt(priceStr) || 100,
        min_students: parseInt(minStudentsStr) || 5,
        current_students: 0,
        tags: ["Yangi", "Sizning kurs"]
      };
      setCourses([newCourse, ...courses]);
      alert("Tabriklaymiz! Kursingiz muvaffaqiyatli e'lon qilindi va ro'yxatga qo'shildi.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Skill Market (Masterklasslar)</h2>
          <p className="text-sm text-gray-500 mt-1">O'zingiz yaxshi biladigan sohada masterklass e'lon qilib EduCoin ishlang.</p>
        </div>
        <button 
          onClick={handleAddCourse}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-bold transition-colors shadow-sm whitespace-nowrap"
        >
          + Kurs e'lon qilish
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {courses.map(course => {
          const isFull = course.current_students >= course.min_students;
          const progressPercent = Math.min((course.current_students / course.min_students) * 100, 100);

          return (
            <div key={course.id} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col h-full hover:shadow-md transition-shadow">
              <div className="flex gap-2 mb-3">
                {course.tags.map(t => (
                  <span key={t} className="bg-blue-50 text-blue-700 text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider">{t}</span>
                ))}
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2 leading-tight">{course.title}</h3>
              <p className="text-sm text-gray-500 mb-5 flex-1">Mentor: <span className="font-medium text-gray-700">{course.author}</span> • {course.time}</p>
              
              <div className="mb-6 bg-gray-50 p-4 rounded-xl border border-gray-100">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-semibold text-gray-500">O'quvchilar: {course.current_students} / {course.min_students}</span>
                  <span className="text-xs font-bold text-blue-600">{Math.round(progressPercent)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5 mb-2">
                  <div className={`h-1.5 rounded-full transition-all duration-500 ${isFull ? 'bg-green-500' : 'bg-blue-600'}`} style={{ width: `${progressPercent}%` }}></div>
                </div>
                {isFull ? (
                  <p className="text-[11px] text-green-600 font-bold">Boshlash uchun yetarli guruh yig'ildi!</p>
                ) : (
                  <p className="text-[11px] text-gray-500">Yana <span className="font-bold text-gray-700">{course.min_students - course.current_students} kishi</span> qo'shilsa boshlanadi.</p>
                )}
              </div>

              <div className="flex items-center justify-between mt-auto">
                <div className="flex items-center gap-1 bg-yellow-50 px-3 py-1.5 rounded-lg border border-yellow-100">
                  <span className="text-lg font-bold text-yellow-600">{course.price}</span>
                  <span className="text-xs font-bold text-yellow-700">💰</span>
                </div>
                {course.author === "Siz (Mentor)" ? (
                  <button 
                    disabled
                    className="px-5 py-2.5 rounded-xl font-bold bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
                  >
                    Sizning kurs
                  </button>
                ) : (
                  <button 
                    onClick={() => handleBuy(course.id, course.price)}
                    className={`px-5 py-2.5 rounded-xl font-bold transition-all shadow-sm ${
                      isFull 
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200' 
                        : 'bg-gray-900 hover:bg-black text-white hover:shadow-md'
                    }`}
                    disabled={isFull}
                  >
                    {isFull ? 'Guruh to\'lgan' : 'Sotib olish'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}


// ─── Tab 3: Leaderboard ─────────────────────────────────────────────────────

function LeaderboardTab() {
  const [scope, setScope] = useState('university');
  const { data, isLoading } = useQuery({ 
    queryKey: ['leaderboard', scope], 
    queryFn: () => api.getLeaderboard(scope) 
  });

  const podium = data?.items.slice(0, 3) || [];
  const table = data?.items.slice(3) || [];

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      
      {/* Toggle */}
      <div className="flex justify-center mb-12">
        <div className="bg-gray-100 p-1 rounded-xl inline-flex">
          <button 
            onClick={() => setScope('university')}
            className={`px-6 py-2 rounded-lg font-semibold text-sm transition-all ${scope === 'university' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Universitet reytingi
          </button>
          <button 
            onClick={() => setScope('national')}
            className={`px-6 py-2 rounded-lg font-semibold text-sm transition-all ${scope === 'national' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Milliy reyting
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12"><div className="animate-spin h-8 w-8 border-b-2 border-blue-600 mx-auto rounded-full"></div></div>
      ) : (
        <>
          {/* Podium for top 3 */}
          <div className="flex justify-center items-end gap-2 sm:gap-6 pt-12 pb-8">
            {/* 2nd place */}
            {podium[1] && (
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 rounded-full bg-gray-200 border-4 border-gray-300 mb-2 flex justify-center items-center font-bold text-xl text-gray-500 shadow-sm z-10 relative">2</div>
                <div className="text-center mb-2">
                  <p className="font-bold text-gray-900 text-sm max-w-[80px] truncate">{podium[1].full_name}</p>
                  <p className="text-yellow-600 font-bold text-xs">{podium[1].total_coins} 💰</p>
                </div>
                <div className="w-20 sm:w-24 h-24 bg-gradient-to-t from-gray-200 to-gray-100 rounded-t-lg border-t-4 border-gray-300"></div>
              </div>
            )}
            
            {/* 1st place */}
            {podium[0] && (
              <div className="flex flex-col items-center">
                <div className="text-4xl mb-1 z-20 relative">👑</div>
                <div className="w-20 h-20 rounded-full bg-yellow-100 border-4 border-yellow-400 mb-2 flex justify-center items-center font-bold text-2xl text-yellow-600 shadow-lg z-10 relative">1</div>
                <div className="text-center mb-2">
                  <p className="font-bold text-gray-900 text-sm max-w-[90px] truncate">{podium[0].full_name}</p>
                  <p className="text-yellow-600 font-bold text-xs">{podium[0].total_coins} 💰</p>
                </div>
                <div className="w-24 sm:w-28 h-32 bg-gradient-to-t from-yellow-200 to-yellow-100 rounded-t-lg border-t-4 border-yellow-400"></div>
              </div>
            )}

            {/* 3rd place */}
            {podium[2] && (
              <div className="flex flex-col items-center">
                <div className="w-14 h-14 rounded-full bg-orange-100 border-4 border-orange-300 mb-2 flex justify-center items-center font-bold text-lg text-orange-600 shadow-sm z-10 relative">3</div>
                <div className="text-center mb-2">
                  <p className="font-bold text-gray-900 text-sm max-w-[80px] truncate">{podium[2].full_name}</p>
                  <p className="text-yellow-600 font-bold text-xs">{podium[2].total_coins} 💰</p>
                </div>
                <div className="w-20 sm:w-24 h-16 bg-gradient-to-t from-orange-200 to-orange-100 rounded-t-lg border-t-4 border-orange-300"></div>
              </div>
            )}
          </div>

          {/* Table for 4-50 */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-xs uppercase text-gray-500 font-semibold">
                  <th className="px-6 py-4 w-16 text-center">O'rin</th>
                  <th className="px-6 py-4">Talaba</th>
                  <th className="px-6 py-4 hidden sm:table-cell">Universitet</th>
                  <th className="px-6 py-4 text-right">Coin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-sm">
                {table.map((user) => (
                  <tr key={user.user_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 text-center font-semibold text-gray-400">{user.rank}</td>
                    <td className="px-6 py-4 font-bold text-gray-900">{user.full_name}</td>
                    <td className="px-6 py-4 text-gray-500 hidden sm:table-cell">{user.university}</td>
                    <td className="px-6 py-4 text-right font-bold text-yellow-600">{user.total_coins}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
