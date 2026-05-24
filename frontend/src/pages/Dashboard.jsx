import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { 
  BookOpen, 
  TrendingUp, 
  Trophy, 
  Coins, 
  Calendar, 
  AlertCircle, 
  CheckCircle2, 
  ChevronRight,
  Clock,
  Send
} from 'lucide-react';

export default function Dashboard({ student, subjects, deadlines, chartData }) {
  // Safe defaults
  const safeStudent = student || {
    name: 'Talaba',
    university: 'Universitet',
    coinBalance: 0,
    avgGrade: 0,
    leaderboardRank: 0,
    totalSubjects: 0,
  };
  const safeSubjects = subjects || [];
  const safeDeadlines = deadlines || [];
  const safeChartData = chartData || [];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* 1. Header Section - Premium Gradient & Glass */}
      <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 shadow-[0_20px_40px_-15px_rgba(79,70,229,0.5)] p-8 sm:p-10 flex flex-col sm:flex-row items-center justify-between gap-6 text-white border border-white/10">
        
        {/* Decorative background patterns */}
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-white opacity-5 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 -ml-16 -mb-16 w-48 h-48 bg-purple-400 opacity-10 rounded-full blur-2xl pointer-events-none"></div>
        
        <div className="relative z-10 flex flex-col sm:items-start text-center sm:text-left">
          <span className="inline-block px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-xs font-semibold uppercase tracking-wider mb-3 text-blue-100 border border-white/20">
            {safeStudent.university}
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Xush kelibsiz, <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-200 to-purple-200">{safeStudent.name}</span> 👋
          </h1>
          <p className="text-blue-200 mt-2 font-medium opacity-90 text-sm sm:text-base">
            O'zlashtirish va davomat ko'rsatkichlaringizni kuzatib boring
          </p>
        </div>
        
        <div className="relative z-10 flex items-center gap-4 bg-white/10 backdrop-blur-xl px-6 py-4 rounded-2xl border border-white/20 shadow-inner hover:scale-105 transition-transform duration-300">
          <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-yellow-400 to-yellow-200 flex items-center justify-center shadow-lg">
            <Coins className="text-yellow-700 w-6 h-6" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-blue-100 font-semibold uppercase tracking-widest opacity-80">EduCoin</span>
            <span className="text-3xl font-black tracking-tight">{safeStudent.coinBalance}</span>
          </div>
        </div>
      </header>

      {/* Quick Stats Row - Glass Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        {[
          { label: "Jami fanlar", value: safeStudent.totalSubjects, icon: BookOpen, color: "from-blue-500 to-blue-400", light: "bg-blue-50 text-blue-600" },
          { label: "O'rtacha baho", value: `${safeStudent.avgGrade}%`, icon: TrendingUp, color: "from-emerald-500 to-emerald-400", light: "bg-emerald-50 text-emerald-600" },
          { label: "Reytingdagi o'rin", value: `#${safeStudent.leaderboardRank}`, icon: Trophy, color: "from-purple-500 to-purple-400", light: "bg-purple-50 text-purple-600" }
        ].map((stat, idx) => (
          <div key={idx} className="group bg-white/60 backdrop-blur-lg p-6 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.02)] border border-white/80 hover:-translate-y-1 hover:shadow-[0_8px_30px_rgb(0,0,0,0.06)] transition-all duration-300">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm text-slate-500 font-medium">{stat.label}</p>
                <p className="text-3xl font-bold text-slate-800 tracking-tight group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-slate-800 group-hover:to-slate-600 transition-colors">
                  {stat.value}
                </p>
              </div>
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${stat.light} transition-transform group-hover:scale-110 duration-300 shadow-sm`}>
                <stat.icon strokeWidth={2.5} className="w-6 h-6" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Telegram Connection Banner */}
      {!safeStudent.telegramLinked && (
        <div className="relative overflow-hidden bg-gradient-to-r from-blue-500 to-cyan-500 rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 text-white shadow-lg border border-blue-400 hover:shadow-xl transition-shadow duration-300">
          <div className="absolute -right-10 -top-10 w-40 h-40 bg-white opacity-10 rounded-full blur-2xl"></div>
          <div className="relative z-10 flex items-center gap-4">
            <div className="w-14 h-14 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center flex-shrink-0">
              <Send className="w-7 h-7 text-white ml-1" />
            </div>
            <div>
              <h3 className="text-xl font-bold">Telegram Botni Ulang</h3>
              <p className="text-blue-50 text-sm mt-1">Darslar, muddatlar va tangalar haqida tezkor xabarnomalar oling</p>
            </div>
          </div>
          <a 
            href="https://t.me/edu_mentorai_bot?start=connect_web" 
            target="_blank" 
            rel="noopener noreferrer"
            className="relative z-10 whitespace-nowrap bg-white text-blue-600 px-6 py-3 rounded-xl font-bold text-sm shadow-md hover:scale-105 hover:bg-blue-50 transition-all duration-300"
          >
            Ulash
          </a>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Main Content Column */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* 2. NB Status Cards */}
          <section className="bg-white/70 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.03)] p-6 sm:p-8 border border-white/80">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-800">NB Holati (Davomat)</h2>
              <button className="flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 px-3 py-1.5 rounded-lg transition-colors">
                Barchasi <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {safeSubjects.map((subject) => {
                let theme = {
                  bg: 'bg-emerald-50/50', border: 'border-emerald-100', text: 'text-emerald-700', 
                  bar: 'bg-gradient-to-r from-emerald-400 to-emerald-500', icon: CheckCircle2
                };

                if (subject.riskLevel === 'warning') {
                  theme = {
                    bg: 'bg-amber-50/50', border: 'border-amber-200', text: 'text-amber-700', 
                    bar: 'bg-gradient-to-r from-amber-400 to-amber-500', icon: AlertCircle
                  };
                } else if (subject.riskLevel === 'critical') {
                  theme = {
                    bg: 'bg-rose-50/50', border: 'border-rose-200', text: 'text-rose-700', 
                    bar: 'bg-gradient-to-r from-rose-500 to-rose-600', icon: AlertCircle
                  };
                }

                const percent = Math.min((subject.currentNb / subject.maxNb) * 100, 100);
                const Icon = theme.icon;

                return (
                  <div key={subject.id} className={`p-5 rounded-2xl border ${theme.bg} ${theme.border} hover:shadow-md transition-shadow cursor-pointer`}>
                    <div className="flex justify-between items-start mb-4">
                      <h3 className={`font-bold ${theme.text} line-clamp-1 flex-1 pr-2`}>{subject.name}</h3>
                      <Icon className={`w-5 h-5 ${theme.text}`} />
                    </div>
                    
                    <div className="mb-1">
                      <div className="flex justify-between text-sm font-bold mb-2">
                        <span className={theme.text}>{subject.currentNb} / {subject.maxNb} NB</span>
                        <span className={theme.text}>{subject.remaining} ta qoldi</span>
                      </div>
                      <div className="h-2.5 w-full bg-white/60 rounded-full overflow-hidden shadow-inner">
                        <div 
                          className={`h-full ${theme.bar} rounded-full transition-all duration-1000 ease-out`}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            {safeSubjects.length === 0 && (
              <div className="text-center py-10">
                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <CheckCircle2 className="w-8 h-8 text-slate-400" />
                </div>
                <p className="text-slate-500 font-medium">Sizda hali NB lar qayd etilmagan.</p>
              </div>
            )}
          </section>

          {/* 4. Subject Performance Chart - Area Gradient */}
          <section className="bg-white/70 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.03)] p-6 sm:p-8 border border-white/80">
            <h2 className="text-2xl font-bold text-slate-800 mb-8">Davomat dinamikasi</h2>
            <div className="h-[320px] w-full">
              {safeChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={safeChartData} margin={{ top: 5, right: 0, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id="colorAttendance" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" opacity={0.5} />
                    <XAxis 
                      dataKey="week" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#64748b', fontSize: 13, fontWeight: 500 }} 
                      dy={15}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#64748b', fontSize: 13, fontWeight: 500 }}
                      domain={[0, 100]}
                      tickFormatter={(val) => `${val}%`}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        borderRadius: '16px', 
                        border: 'none', 
                        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        backdropFilter: 'blur(8px)',
                        fontWeight: 600,
                        color: '#0f172a'
                      }}
                      itemStyle={{ color: '#4f46e5', fontWeight: 700 }}
                      formatter={(value) => [`${value}%`, 'Davomat']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="attendance" 
                      stroke="#4f46e5" 
                      strokeWidth={4}
                      fillOpacity={1} 
                      fill="url(#colorAttendance)" 
                      activeDot={{ r: 8, strokeWidth: 0, fill: '#4f46e5', style: {filter: 'drop-shadow(0px 4px 6px rgba(79, 70, 229, 0.5))'} }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
                  <TrendingUp className="w-12 h-12 mb-2 opacity-50" />
                  <span className="font-medium">Grafik uchun ma'lumot yetarli emas</span>
                </div>
              )}
            </div>
          </section>

        </div>

        {/* Sidebar Column */}
        <div className="space-y-8">
          
          {/* 3. Upcoming Deadlines */}
          <section className="bg-white/70 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.03)] p-6 sm:p-8 border border-white/80 sticky top-24">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-indigo-500" /> Muddatlar
              </h2>
              <span className="bg-indigo-50 text-indigo-700 text-xs font-bold px-2.5 py-1 rounded-md border border-indigo-100">
                7 kun
              </span>
            </div>
            
            <div className="space-y-4">
              {safeDeadlines.map((deadline) => {
                const isUrgent = deadline.daysAway <= 2;
                const isToday = deadline.daysAway === 0;

                return (
                  <div 
                    key={deadline.id} 
                    className={`group relative p-4 rounded-2xl border transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 ${
                      isUrgent ? 'bg-rose-50/30 border-rose-100 hover:border-rose-300' : 'bg-white border-slate-100 hover:border-indigo-200'
                    }`}
                  >
                    <div className="flex gap-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors ${
                        deadline.type === 'Oraliq nazorat' || deadline.type === 'Yakuniy' 
                          ? 'bg-gradient-to-br from-indigo-100 to-purple-100 text-indigo-600 group-hover:from-indigo-200 group-hover:to-purple-200' 
                          : 'bg-gradient-to-br from-blue-50 to-cyan-50 text-blue-500 group-hover:from-blue-100 group-hover:to-cyan-100'
                      }`}>
                        {deadline.type === 'Oraliq nazorat' || deadline.type === 'Yakuniy' ? <Trophy className="w-5 h-5" /> : <BookOpen className="w-5 h-5" />}
                      </div>
                      <div className="flex-1 min-w-0 flex flex-col justify-center">
                        <h4 className="font-bold text-slate-800 text-[15px] truncate">{deadline.subject}</h4>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs font-semibold text-slate-500">{deadline.type}</span>
                          <span className="text-slate-300">•</span>
                          <span className={`text-xs font-bold flex items-center gap-1 ${
                            isToday ? 'text-rose-600' : isUrgent ? 'text-amber-600' : 'text-indigo-600'
                          }`}>
                            <Clock className="w-3 h-3" />
                            {isToday ? 'Bugun!' : `${deadline.daysAway} kun`}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {safeDeadlines.length === 0 && (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-3">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                  </div>
                  <p className="text-slate-500 text-sm font-medium">Yaqin 7 kunda hech qanday muddat yo'q, dam oling!</p>
                </div>
              )}
            </div>
            
            <button className="w-full mt-6 py-3 bg-slate-50 hover:bg-slate-100 text-slate-700 text-sm font-bold rounded-xl transition-colors border border-slate-200/60 shadow-sm">
              To'liq taqvimni ochish
            </button>
          </section>
          
        </div>
      </div>
    </div>
  );
}
