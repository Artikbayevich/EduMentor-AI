import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard';
import LessonPage from './pages/LessonPage';
import P2PMarketplace from './pages/P2PMarketplace';
import HemisTeacherDemo from './pages/HemisTeacherDemo';

// Refactored mock data to match component expectations
const MOCK_USER = { 
  name: "Akbarali", // fixed from full_name
  university: "Muhammad al-Xorazmiy nomidagi TATU", 
  coinBalance: 1500, // fixed from coin_balance
  avgGrade: 85,
  leaderboardRank: 12,
  totalSubjects: 8,
  telegramLinked: false // show banner
};

const MOCK_SUBJECTS = [
  { id: 1, name: "Fizika", currentNb: 1, maxNb: 5, remaining: 4, riskLevel: 'safe' }, // mapped props
  { id: 2, name: "Kriptografiya asoslari", currentNb: 4, maxNb: 5, remaining: 1, riskLevel: 'critical' },
  { id: 3, name: "Dasturlash II", currentNb: 2, maxNb: 5, remaining: 3, riskLevel: 'warning' }
];

const MOCK_DEADLINES = [
  { id: 1, subject: "Ma'lumotlar bazasi", type: "Oraliq nazorat", daysAway: 2 }, // mapped props
  { id: 2, subject: "Kriptografiya", type: "Topshiriq", daysAway: 0 },
  { id: 3, subject: "Dasturlash II", type: "Yakuniy", daysAway: 5 }
];

const MOCK_CHART_DATA = [
  { week: '1-hafta', attendance: 100 }, 
  { week: '2-hafta', attendance: 85 },
  { week: '3-hafta', attendance: 90 },
  { week: '4-hafta', attendance: 70 },
  { week: '5-hafta', attendance: 95 }
];

const queryClient = new QueryClient();

function NavLink({ to, children }) {
  const location = useLocation();
  const isActive = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
  
  return (
    <Link 
      to={to} 
      className={`px-4 py-2 rounded-xl transition-all duration-300 font-medium ${
        isActive 
          ? 'bg-blue-600/10 text-blue-600 shadow-sm' 
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
      }`}
    >
      {children}
    </Link>
  );
}

function Layout({ children }) {
  return (
    <div className="min-h-screen font-sans bg-[#f8fafc] text-slate-900 selection:bg-blue-200 selection:text-blue-900 relative">
      
      {/* Background ambient light effects */}
      <div className="fixed top-[-10%] left-[-10%] w-96 h-96 bg-blue-400/20 blur-[120px] rounded-full pointer-events-none"></div>
      <div className="fixed bottom-[10%] right-[-5%] w-[30rem] h-[30rem] bg-indigo-400/10 blur-[150px] rounded-full pointer-events-none"></div>

      {/* Floating Glassmorphism Navbar */}
      <nav className="sticky top-4 z-50 mx-4 sm:mx-8 lg:mx-auto max-w-4xl mt-4">
        <div className="bg-white/70 backdrop-blur-md border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-2xl p-2 flex gap-1 overflow-x-auto hide-scrollbar">
          <NavLink to="/dashboard">🏠 Bosh sahifa</NavLink>
          <NavLink to="/lesson/1">📚 Dars (Demo)</NavLink>
          <NavLink to="/p2p">🤝 P2P Bozor</NavLink>
          <NavLink to="/teacher-demo">👨‍🏫 O'qituvchi Demo</NavLink>
        </div>
      </nav>
      
      <main className="pb-16 pt-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {children}
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/dashboard" element={<Dashboard student={MOCK_USER} subjects={MOCK_SUBJECTS} deadlines={MOCK_DEADLINES} chartData={MOCK_CHART_DATA} />} />
            <Route path="/lesson/:lessonId" element={<LessonPage />} />
            <Route path="/p2p" element={<P2PMarketplace />} />
            <Route path="/teacher-demo" element={<HemisTeacherDemo />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
