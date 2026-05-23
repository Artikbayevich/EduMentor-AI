import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function Dashboard({ student, subjects, deadlines, chartData }) {
  // Safe defaults if props are not yet loaded
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
    <div className="min-h-screen bg-gray-50 text-gray-900 p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* 1. Header Section */}
        <header className="bg-white rounded-2xl shadow-sm p-6 flex flex-col sm:flex-row items-center justify-between gap-4 border border-gray-100">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900">
              Assalomu alaykum, {safeStudent.name} 👋
            </h1>
            <p className="text-sm text-gray-500 mt-1 font-medium">{safeStudent.university}</p>
          </div>
          <div className="flex items-center gap-2 bg-yellow-50 px-4 py-2 rounded-xl border border-yellow-200 shadow-inner">
            <span className="text-xl">💰</span>
            <div className="flex flex-col">
              <span className="text-xs text-yellow-700 font-semibold uppercase tracking-wider">EduCoin</span>
              <span className="text-lg font-bold text-yellow-600 leading-none">{safeStudent.coinBalance}</span>
            </div>
          </div>
        </header>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Jami fanlar</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{safeStudent.totalSubjects}</p>
            </div>
            <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center text-blue-500 text-xl">📚</div>
          </div>
          <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">O'rtacha baho</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{safeStudent.avgGrade}%</p>
            </div>
            <div className="w-12 h-12 bg-green-50 rounded-full flex items-center justify-center text-green-500 text-xl">📈</div>
          </div>
          <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Reytingdagi o'rin</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">#{safeStudent.leaderboardRank}</p>
            </div>
            <div className="w-12 h-12 bg-purple-50 rounded-full flex items-center justify-center text-purple-500 text-xl">🏆</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Main Content Column */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* 2. NB Status Cards */}
            <section className="bg-white rounded-2xl shadow-sm p-6 border border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">NB Holati (Davomat)</h2>
                <a href="/attendance" className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors">Barchasi →</a>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {safeSubjects.map((subject) => {
                  let colorClass = 'bg-green-50 border-green-200';
                  let textColor = 'text-green-700';
                  let barColor = 'bg-green-500';
                  let icon = '✅';

                  if (subject.riskLevel === 'warning') {
                    colorClass = 'bg-yellow-50 border-yellow-200';
                    textColor = 'text-yellow-700';
                    barColor = 'bg-yellow-500';
                    icon = '⚠️';
                  } else if (subject.riskLevel === 'critical') {
                    colorClass = 'bg-red-50 border-red-200';
                    textColor = 'text-red-700';
                    barColor = 'bg-red-500';
                    icon = '🔴';
                  }

                  const percent = Math.min((subject.currentNb / subject.maxNb) * 100, 100);

                  return (
                    <div key={subject.id} className={`p-4 rounded-xl border ${colorClass} transition-transform hover:scale-[1.02] duration-200 cursor-pointer`}>
                      <div className="flex justify-between items-start mb-3">
                        <h3 className={`font-semibold ${textColor} line-clamp-1 flex-1 pr-2`}>{subject.name}</h3>
                        <span className="text-sm" title={subject.riskLevel}>{icon}</span>
                      </div>
                      
                      <div className="mb-2">
                        <div className="flex justify-between text-xs font-medium mb-1">
                          <span className={textColor}>{subject.currentNb} / {subject.maxNb} NB</span>
                          <span className={textColor}>{subject.remaining} ta qoldi</span>
                        </div>
                        <div className="h-2 w-full bg-white/50 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${barColor} rounded-full transition-all duration-500`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              {safeSubjects.length === 0 && (
                <div className="text-center py-8 text-gray-400 font-medium">NB ma'lumotlari yo'q</div>
              )}
            </section>

            {/* 4. Subject Performance Chart */}
            <section className="bg-white rounded-2xl shadow-sm p-6 border border-gray-100">
              <h2 className="text-xl font-bold text-gray-900 mb-6">Davomat dinamikasi</h2>
              <div className="h-[300px] w-full">
                {safeChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={safeChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                      <XAxis 
                        dataKey="week" 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fill: '#6b7280', fontSize: 12 }} 
                        dy={10}
                      />
                      <YAxis 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                        domain={[0, 100]}
                        tickFormatter={(val) => `${val}%`}
                      />
                      <Tooltip 
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                        formatter={(value) => [`${value}%`, 'Davomat']}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="attendance" 
                        stroke="#3b82f6" 
                        strokeWidth={3}
                        dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
                        activeDot={{ r: 6, strokeWidth: 0 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400 font-medium">
                    Grafik uchun ma'lumot yetarli emas
                  </div>
                )}
              </div>
            </section>

          </div>

          {/* Sidebar Column */}
          <div className="space-y-6">
            
            {/* 3. Upcoming Deadlines */}
            <section className="bg-white rounded-2xl shadow-sm p-6 border border-gray-100 sticky top-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Yaqin muddatlar</h2>
                <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-1 rounded-lg">7 kun</span>
              </div>
              
              <div className="space-y-3">
                {safeDeadlines.map((deadline) => {
                  const isUrgent = deadline.daysAway <= 2;
                  const isToday = deadline.daysAway === 0;

                  return (
                    <div 
                      key={deadline.id} 
                      className={`p-3 rounded-xl border flex gap-3 transition-colors ${
                        isUrgent ? 'bg-red-50/50 border-red-100' : 'bg-white border-gray-100 hover:border-blue-100'
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 text-xl ${
                        deadline.type === 'exam' ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'
                      }`}>
                        {deadline.type === 'exam' ? '📝' : '📌'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-gray-900 text-sm truncate">{deadline.subject}</h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-gray-500 capitalize">{deadline.type}</span>
                          <span className="text-gray-300">•</span>
                          <span className={`text-xs font-bold ${
                            isToday ? 'text-red-600' : isUrgent ? 'text-orange-500' : 'text-blue-600'
                          }`}>
                            {isToday ? 'Bugun!' : `${deadline.daysAway} kun qoldi`}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {safeDeadlines.length === 0 && (
                  <div className="text-center py-6">
                    <div className="text-3xl mb-2">🎉</div>
                    <p className="text-gray-500 text-sm font-medium">Yaqin 7 kunda hech qanday muddat yo'q</p>
                  </div>
                )}
              </div>
              
              <button className="w-full mt-4 py-2.5 bg-gray-50 hover:bg-gray-100 text-gray-700 text-sm font-semibold rounded-xl transition-colors border border-gray-200">
                To'liq jadvalni ko'rish
              </button>
            </section>
            
          </div>
        </div>

      </div>
    </div>
  );
}
