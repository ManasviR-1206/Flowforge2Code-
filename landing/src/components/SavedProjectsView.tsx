import React, { useState, useEffect } from 'react';
import { Bookmark, Trash2, ArrowRight, Clock, Code } from 'lucide-react';

interface SavedProjectsViewProps {
  onLoadProject: (project: any) => void;
}

export const SavedProjectsView: React.FC<SavedProjectsViewProps> = ({ onLoadProject }) => {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/projects');
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this saved project?')) return;
    try {
      const res = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchProjects();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleOpen = async (id: string) => {
    try {
      const res = await fetch(`/api/projects/${id}`);
      if (res.ok) {
        const fullProject = await res.json();
        onLoadProject(fullProject);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2.5">
            <Bookmark className="w-6 h-6 text-indigo-600" />
            Saved Projects
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Revisit, open, and continue working on your flowcharts and generated Python code.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400 font-medium text-sm">
          Loading saved projects...
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center max-w-md mx-auto space-y-3 shadow-xs">
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto text-xl">
            📁
          </div>
          <h3 className="font-bold text-gray-800 text-lg">No Saved Projects Yet</h3>
          <p className="text-xs text-gray-500">
            Create or edit a flowchart on the dashboard canvas and click "Save Project" to store it here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((p) => (
            <div
              key={p.id}
              onClick={() => handleOpen(p.id)}
              className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <h3 className="font-bold text-gray-800 group-hover:text-indigo-600 transition-colors line-clamp-1">
                    {p.name || 'Untitled Flowchart'}
                  </h3>
                  <button
                    onClick={(e) => handleDelete(p.id, e)}
                    className="p-1 text-gray-300 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                    title="Delete project"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <div className="flex items-center gap-2 text-xs text-gray-400 mb-4">
                  <Clock size={14} />
                  <span>
                    {p.updated_at ? new Date(p.updated_at).toLocaleDateString() : 'Recently saved'}
                  </span>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 flex items-center justify-between text-xs font-semibold text-indigo-600 group-hover:translate-x-1 transition-transform">
                <span className="flex items-center gap-1.5 text-gray-600 font-medium">
                  <Code size={14} className="text-indigo-500" /> Open Flowchart
                </span>
                <ArrowRight size={16} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
