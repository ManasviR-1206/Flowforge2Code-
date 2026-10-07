import React, { useState } from 'react';
import { MessageSquare, Send, CheckCircle2 } from 'lucide-react';

export const FeedbackView: React.FC = () => {
  const [feedback, setFeedback] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;
    setSubmitted(true);
    setFeedback('');
    setTimeout(() => setSubmitted(false), 4000);
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2.5">
          <MessageSquare className="w-6 h-6 text-indigo-600" />
          Feedback & Suggestions
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          We'd love to hear your thoughts, bug reports, or feature suggestions for FlowForge AI.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-xs">
        {submitted ? (
          <div className="py-8 text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto" />
            <h3 className="font-bold text-gray-800 text-lg">Thank You for your Feedback!</h3>
            <p className="text-xs text-gray-500">Your message has been sent to the FlowForge AI development team.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-2">
                Your Feedback or Feature Request
              </label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={5}
                placeholder="Share your experience using FlowForge AI..."
                className="w-full bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-800 focus:outline-none focus:border-indigo-500 focus:bg-white transition-all"
              />
            </div>
            <button
              type="submit"
              disabled={!feedback.trim()}
              className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white font-semibold text-sm rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-50 shadow-sm"
            >
              <Send size={16} />
              Submit Feedback
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
