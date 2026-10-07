import React from 'react';
import { 
  Home, 
  PlusSquare, 
  UploadCloud, 
  Code2, 
  Play, 
  Clock, 
  Bookmark, 
  Settings, 
  HelpCircle, 
  MessageSquare
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const mainNavItems = [
    { name: 'Dashboard', key: 'dashboard', icon: Home },
    { name: 'Create Flowchart', key: 'create', icon: PlusSquare },
    { name: 'Upload Image', key: 'upload', icon: UploadCloud },
    { name: 'Generate Code', key: 'generate', icon: Code2 },
    { name: 'Run & Output', key: 'run', icon: Play },
    { name: 'History', key: 'history', icon: Clock },
    { name: 'Saved Projects', key: 'projects', icon: Bookmark },
  ];

  const bottomNavItems = [
    { name: 'Settings & API Keys', key: 'settings', icon: Settings },
    { name: 'Help & Docs', key: 'docs', icon: HelpCircle },
    { name: 'Feedback', key: 'feedback', icon: MessageSquare },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-100 flex flex-col h-screen sticky top-0 shrink-0 z-20 shadow-sm">
      <div className="p-4 flex flex-col gap-1.5 flex-grow overflow-y-auto">
        {mainNavItems.map((item) => {
          const isActive = activeTab === item.key;
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              onClick={() => setActiveTab(item.key)}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-semibold text-sm w-full text-left ${
                isActive
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-md shadow-indigo-500/20'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon size={18} className={isActive ? 'text-white' : 'text-gray-500'} />
              {item.name}
            </button>
          );
        })}

        <div className="mt-auto pt-6 flex flex-col gap-1.5 border-t border-gray-100">
          {bottomNavItems.map((item) => {
            const isActive = activeTab === item.key;
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key)}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all font-semibold text-sm w-full text-left ${
                  isActive
                    ? 'bg-blue-50 text-blue-600 border border-blue-100'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon size={18} className={isActive ? 'text-blue-600' : 'text-gray-500'} />
                {item.name}
              </button>
            );
          })}
        </div>

        {/* AI Robot Banner Card matching reference image */}
        <div className="mt-6 bg-gradient-to-br from-indigo-50/80 via-blue-50 to-purple-50 rounded-2xl p-4 flex flex-col items-center text-center border border-indigo-100/50 shadow-sm">
          <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center mb-3 shadow-md border border-indigo-50 text-2xl">
            🤖
          </div>
          <h4 className="text-xs font-bold text-gray-800 leading-snug mb-1">
            Turn your Flowcharts into Code with AI
          </h4>
          <p className="text-[11px] font-medium text-gray-500">Simple. Smart. Fast. ✨</p>
        </div>
      </div>
    </aside>
  );
};
