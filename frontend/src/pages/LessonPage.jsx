import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';

// Mock API functions (replace with your actual API calls)
const fetchLessonSummary = async (lessonId) => {
  const res = await fetch(`/api/v1/lessons/${lessonId}`);
  if (!res.ok) throw new Error('Dars xulosasini yuklashda xatolik');
  return res.json();
};

const fetchLessonTest = async (lessonId) => {
  const res = await fetch(`/api/v1/lessons/${lessonId}/test`);
  if (!res.ok) throw new Error('Test yuklashda xatolik');
  return res.json();
};

const submitTestAnswers = async ({ lessonId, answers }) => {
  const res = await fetch(`/api/v1/lessons/${lessonId}/test/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error('Javoblarni yuborishda xatolik');
  return res.json();
};

export default function LessonPage() {
  const { lessonId } = useParams();
  const [testStarted, setTestStarted] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState({});
  const [selectedOption, setSelectedOption] = useState(null);

  // Queries
  const { data: lesson, isLoading: lessonLoading, error: lessonError } = useQuery({
    queryKey: ['lesson', lessonId],
    queryFn: () => fetchLessonSummary(lessonId),
  });

  const { data: testData, isLoading: testLoading, error: testError } = useQuery({
    queryKey: ['lessonTest', lessonId],
    queryFn: () => fetchLessonTest(lessonId),
    enabled: testStarted, // Only fetch when user clicks start test
  });

  const submitMutation = useMutation({
    mutationFn: submitTestAnswers,
  });

  if (lessonLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (lessonError) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
        <p className="text-red-600 mb-4">{lessonError.message}</p>
        <button onClick={() => window.history.back()} className="text-blue-600 hover:underline">
          &larr; Ortga qaytish
        </button>
      </div>
    );
  }

  // Parse markdown summary and extract bullet points if possible
  // In a real app, the API might return structured key points. Here we'll just split by bullet points if they exist.
  const summaryText = lesson?.summary || '';
  const keyPoints = summaryText.split('\n').filter(line => line.trim().startsWith('-'));

  const handleNextQuestion = () => {
    const questions = testData?.questions || [];
    
    // Save answer
    if (selectedOption) {
      setUserAnswers(prev => ({
        ...prev,
        [currentQuestionIndex]: selectedOption.charAt(0) // Extract "A", "B", "C", or "D"
      }));
    }

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
      setSelectedOption(null);
    } else {
      // Finished all questions, submit
      submitMutation.mutate({
        lessonId,
        answers: {
          ...userAnswers,
          [currentQuestionIndex]: selectedOption ? selectedOption.charAt(0) : null
        }
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 pb-12 font-sans">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-8 space-y-8">
        
        {/* Navigation */}
        <button 
          onClick={() => window.location.href = '/dashboard'} 
          className="flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
        >
          <span className="mr-2">&larr;</span> Bosh sahifaga qaytish
        </button>

        {/* 1. Header */}
        <header className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-gray-100">
          <div className="flex items-center gap-3 mb-4">
            <span className="bg-red-100 text-red-700 text-xs font-bold px-3 py-1 rounded-full">
              Qoldirilgan dars
            </span>
            <span className="text-sm font-medium text-gray-500">
              Bugun
            </span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 leading-tight mb-2">
            {lesson?.subject}
          </h1>
          <h2 className="text-xl text-gray-600 font-medium">
            Mavzu: {lesson?.topic}
          </h2>
        </header>

        {/* 2 & 3. Summary & Key Points */}
        <main className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-gray-100 prose prose-blue max-w-none">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-xl">
              🤖
            </div>
            <h3 className="text-xl font-bold text-gray-900 m-0">AI dars xulosasi</h3>
          </div>
          
          <div className="text-gray-700 leading-relaxed mb-8">
            <ReactMarkdown>{summaryText}</ReactMarkdown>
          </div>

          {keyPoints.length > 0 && (
            <div className="bg-blue-50 rounded-xl p-6 border border-blue-100">
              <h4 className="text-blue-900 font-bold mb-4 mt-0">Asosiy tushunchalar:</h4>
              <ul className="space-y-2 text-blue-800 m-0 pl-5">
                {keyPoints.map((point, idx) => (
                  <li key={idx}>{point.replace(/^-\s*/, '')}</li>
                ))}
              </ul>
            </div>
          )}
        </main>

        {/* 4. Interactive Test Section */}
        <section className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-gray-100">
          {!testStarted ? (
            <div className="text-center py-8">
              <div className="text-5xl mb-4">📝</div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">Bilimni tekshirish</h3>
              <p className="text-gray-500 mb-8 max-w-md mx-auto">
                Dars materialini o'qib chiqqan bo'lsangiz, qisqa test yechib o'zlashtirishingizni tekshiring va EduCoin ishlang!
              </p>
              <button
                onClick={() => setTestStarted(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-xl transition-colors shadow-sm"
              >
                Testni boshlash
              </button>
            </div>
          ) : (
            <div>
              {testLoading && (
                <div className="py-12 flex flex-col items-center justify-center">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
                  <p className="text-gray-500 font-medium">AI test savollarini tayyorlamoqda...</p>
                </div>
              )}
              
              {testError && (
                <div className="py-8 text-center">
                  <p className="text-red-600 font-medium">{testError.message}</p>
                </div>
              )}

              {testData && !submitMutation.isSuccess && (
                <div className="max-w-2xl mx-auto">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="text-xl font-bold text-gray-900">
                      Savol {currentQuestionIndex + 1} / {testData.questions.length}
                    </h3>
                    <div className="text-sm font-medium text-gray-500">
                      Mavzu: {testData.topic}
                    </div>
                  </div>

                  <div className="mb-8">
                    <p className="text-lg text-gray-800 font-medium leading-relaxed mb-6">
                      {testData.questions[currentQuestionIndex].question}
                    </p>

                    <div className="space-y-3">
                      {testData.questions[currentQuestionIndex].options.map((option, idx) => {
                        const isSelected = selectedOption === option;
                        return (
                          <button
                            key={idx}
                            onClick={() => setSelectedOption(option)}
                            className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                              isSelected 
                                ? 'border-blue-600 bg-blue-50 text-blue-900 font-medium' 
                                : 'border-gray-200 hover:border-gray-300 text-gray-700'
                            }`}
                          >
                            {option}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={handleNextQuestion}
                      disabled={!selectedOption || submitMutation.isPending}
                      className="bg-gray-900 hover:bg-black text-white font-bold py-3 px-8 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {submitMutation.isPending ? 'Yuborilmoqda...' : 
                        (currentQuestionIndex === testData.questions.length - 1 ? 'Yakunlash' : 'Keyingisi')}
                    </button>
                  </div>
                </div>
              )}

              {submitMutation.isSuccess && (
                <div className="py-8 text-center max-w-lg mx-auto">
                  <div className="text-6xl mb-6">🎉</div>
                  <h3 className="text-3xl font-bold text-gray-900 mb-2">
                    Test yakunlandi!
                  </h3>
                  <div className="inline-block bg-yellow-50 border border-yellow-200 rounded-2xl p-6 mb-8 mt-4 w-full">
                    <p className="text-gray-600 mb-1 font-medium">Sizning natijangiz:</p>
                    <p className="text-4xl font-bold text-gray-900 mb-4">
                      {submitMutation.data.percentage}%
                    </p>
                    <div className="flex items-center justify-center gap-2 text-yellow-700 font-bold bg-yellow-100 py-2 rounded-lg">
                      <span>💰</span> +{submitMutation.data.coins_earned} EduCoin ishladingiz!
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <button 
                      onClick={() => window.location.href = '/dashboard'}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 px-8 rounded-xl transition-colors"
                    >
                      Bosh panelga qaytish
                    </button>
                    <button 
                      onClick={() => window.location.href = '/p2p'}
                      className="w-full bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 font-bold py-3.5 px-8 rounded-xl transition-colors"
                    >
                      Mavzuni tushunmadingizmi? Mentor qidiring
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
