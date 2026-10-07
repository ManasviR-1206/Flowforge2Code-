import React from 'react';
import { Sidebar } from './Sidebar';
import { WorkspaceHeader } from './WorkspaceHeader';

interface WorkspaceLayoutProps {
  children: React.ReactNode;
  activeTab?: string;
  setActiveTab?: (tab: string) => void;
}

export const WorkspaceLayout: React.FC<WorkspaceLayoutProps> = ({ 
  children, 
  activeTab = 'dashboard', 
  setActiveTab = () => {} 
}) => {
  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col font-sans text-gray-900">
      <WorkspaceHeader setActiveTab={setActiveTab} />
      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-[#F8FAFC]">
          {children}
        </main>
      </div>
    </div>
  );
};
