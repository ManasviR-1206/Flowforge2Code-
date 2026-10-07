import React, { useState, useEffect } from 'react';
import { Key, Plus, Trash2, Copy, Check, ShieldCheck, Eye, EyeOff } from 'lucide-react';

export const ApiKeysSettingsView: React.FC = () => {
  const [keys, setKeys] = useState<any[]>([]);
  const [keyName, setKeyName] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<{ [key: string]: boolean }>({});
  const [userGeminiKey, setUserGeminiKey] = useState(localStorage.getItem('ff_gemini_key') || '');
  const [savedGeminiStatus, setSavedGeminiStatus] = useState(false);

  const fetchKeys = async () => {
    try {
      const res = await fetch('/api/keys');
      if (res.ok) {
        const data = await res.json();
        setKeys(data);
      }
    } catch (e) {
      console.error('Failed to fetch API keys', e);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: keyName.trim() }),
      });
      if (res.ok) {
        setKeyName('');
        await fetchKeys();
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleRevokeKey = async (id: string) => {
    try {
      const res = await fetch(`/api/keys/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchKeys();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleKey = async (id: string) => {
    try {
      const res = await fetch(`/api/keys/${id}/toggle`, { method: 'PUT' });
      if (res.ok) {
        fetchKeys();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const saveGeminiKey = () => {
    localStorage.setItem('ff_gemini_key', userGeminiKey);
    setSavedGeminiStatus(true);
    setTimeout(() => setSavedGeminiStatus(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2.5">
          <Key className="w-6 h-6 text-indigo-600" />
          API Keys & Settings
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Manage your FlowForge AI access tokens and LLM credentials.
        </p>
      </div>

      {/* Gemini API Key Box */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h3 className="text-base font-bold text-gray-800 flex items-center gap-2 mb-2">
          <ShieldCheck className="w-5 h-5 text-green-500" />
          LLM Provider Key (Optional Gemini Key)
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Provide your custom Gemini API key for AI code generation, or rely on our built-in AST compiler.
        </p>
        <div className="flex gap-3 max-w-lg">
          <input
            type="password"
            value={userGeminiKey}
            onChange={(e) => setUserGeminiKey(e.target.value)}
            placeholder="AIzaSy..."
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 focus:bg-white transition-all font-mono"
          />
          <button
            onClick={saveGeminiKey}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-all shadow-sm"
          >
            {savedGeminiStatus ? 'Saved!' : 'Save Key'}
          </button>
        </div>
      </div>

      {/* FlowForge API Keys Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-gray-100 pb-4">
          <div>
            <h3 className="text-base font-bold text-gray-800">Your FlowForge API Keys</h3>
            <p className="text-xs text-gray-500">API keys allow external applications to interact with FlowForge endpoints.</p>
          </div>
        </div>

        {/* Create Form */}
        <form onSubmit={handleCreateKey} className="flex gap-3 max-w-md">
          <input
            type="text"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            placeholder="Key Name (e.g. Production Backend)"
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-indigo-500 focus:bg-white"
          />
          <button
            type="submit"
            disabled={loading || !keyName.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-all disabled:opacity-50"
          >
            <Plus size={16} />
            {loading ? 'Creating...' : 'Create Key'}
          </button>
        </form>

        {/* Keys List */}
        <div className="overflow-hidden border border-gray-100 rounded-xl">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 border-b border-gray-100 text-xs font-bold text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="p-3.5">Name</th>
                <th className="p-3.5">Key Token</th>
                <th className="p-3.5">Created</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {keys.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-gray-400 text-xs">
                    No API keys created yet. Create one above to get started.
                  </td>
                </tr>
              ) : (
                keys.map((k) => (
                  <tr key={k.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="p-3.5 font-bold text-gray-800">{k.name}</td>
                    <td className="p-3.5 font-mono text-xs text-gray-600">
                      {showKeys[k.id] ? k.key : `${k.key.substring(0, 7)}...${k.key.substring(k.key.length - 4)}`}
                    </td>
                    <td className="p-3.5 text-xs text-gray-500">
                      {k.created_at ? new Date(k.created_at).toLocaleDateString() : 'Just now'}
                    </td>
                    <td className="p-3.5">
                      <button
                        onClick={() => handleToggleKey(k.id)}
                        className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                          k.is_active
                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {k.is_active ? 'Active' : 'Disabled'}
                      </button>
                    </td>
                    <td className="p-3.5 text-right flex items-center justify-end gap-2">
                      <button
                        onClick={() => setShowKeys((prev) => ({ ...prev, [k.id]: !prev[k.id] }))}
                        className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                        title="Toggle view"
                      >
                        {showKeys[k.id] ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                      <button
                        onClick={() => copyToClipboard(k.key, k.id)}
                        className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                        title="Copy Key"
                      >
                        {copiedId === k.id ? <Check size={15} className="text-green-600" /> : <Copy size={15} />}
                      </button>
                      <button
                        onClick={() => handleRevokeKey(k.id)}
                        className="p-1.5 text-red-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                        title="Revoke Key"
                      >
                        <Trash2 size={15} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
