import React, { useState } from 'react';
import axios from 'axios';

export default function HemisTeacherDemo() {
  const [studentId, setStudentId] = useState('admin_hemis'); // Akbarali by default
  const [subject, setSubject] = useState('Fizika');
  const [topic, setTopic] = useState('Termodinamikaning 1-qonuni');
  const [pdfContent, setPdfContent] = useState(
    'Termodinamikaning birinchi qonuni energiyaning saqlanish qonunidir. Izotermik, izobarik va izoxorik jarayonlar muhim ahamiyatga ega. Tizimga berilgan issiqlik uning ichki energiyasini oshirishga va ish bajarishga sarflanadi.'
  );
  
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const res = await axios.post('/api/v1/lessons/mock-nb', {
        student_id: studentId,
        subject_name: subject,
        lesson_topic: topic,
        pdf_content: pdfContent
      });
      setMessage({ type: 'success', text: res.data.message || 'Muvaffaqiyatli saqlandi!' });
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Xatolik yuz berdi' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4 font-sans">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-lg w-full border-t-4 border-blue-800">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800">HEMIS O'qituvchi Kabineti</h2>
          <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded font-bold">Demo Mode</span>
        </div>
        
        <p className="text-gray-600 mb-6 text-sm">
          Bu sahifa orqali jurnalga NB qo'yilganida talabaga va AI tizimiga xabar qanday yetib borishini ko'rsatib berishingiz mumkin.
        </p>

        {message && (
          <div className={`p-4 mb-6 rounded-lg text-sm ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Talaba HEMIS ID</label>
            <input 
              type="text" 
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Masalan: admin_hemis"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Fan nomi</label>
            <select 
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="Fizika">Fizika</option>
              <option value="Oliy Matematika">Oliy Matematika</option>
              <option value="Dasturlash">Dasturlash (Python)</option>
              <option value="Ingliz tili">Ingliz tili</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Bugungi dars mavzusi</label>
            <input 
              type="text" 
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Dars materiali (PDF o'rniga matn)</label>
            <textarea 
              rows={4}
              value={pdfContent}
              onChange={(e) => setPdfContent(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
              placeholder="Dars matni (qisqacha)..."
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4 rounded-lg transition-colors flex justify-center items-center gap-2"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              "Jurnalga 'NB' qoyish va Saqlash"
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <a href="/dashboard" className="text-blue-600 hover:underline text-sm font-medium">
            Tizimga (Talaba profiliga) qaytish
          </a>
        </div>
      </div>
    </div>
  );
}
