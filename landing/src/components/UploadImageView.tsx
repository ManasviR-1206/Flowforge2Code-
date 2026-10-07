import React, { useState } from 'react';
import { UploadCloud, Sparkles, CheckCircle2, ArrowRight } from 'lucide-react';

interface UploadImageViewProps {
  onAnalyzeSuccess: (data: { blocks: any[]; connections: any[] }) => void;
}

export const UploadImageView: React.FC<UploadImageViewProps> = ({ onAnalyzeSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setAnalysisResult(null);
      setError(null);
    }
  };

  const handleAnalyze = async (mode: 'upload' | 'sample') => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('mode', mode);
      if (mode === 'upload' && selectedFile) {
        formData.append('file', selectedFile);
      }

      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Analysis failed on backend');
      }

      const data = await res.json();
      setAnalysisResult(data);
    } catch (err: any) {
      setError(err.message || 'Image analysis failed.');
    }
    setLoading(false);
  };

  const handleImportToCanvas = () => {
    if (analysisResult) {
      onAnalyzeSuccess({
        blocks: analysisResult.blocks || [],
        connections: analysisResult.connections || [],
      });
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2.5">
          <UploadCloud className="w-6 h-6 text-indigo-600" />
          Upload Flowchart Image
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Upload a hand-drawn or digital image of a flowchart. FlowForge AI detects shapes, extracts text using OCR, and builds an interactive flowchart!
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Upload Dropzone */}
        <div className="bg-white rounded-2xl border-2 border-dashed border-gray-200 p-8 flex flex-col items-center justify-center text-center space-y-4 hover:border-indigo-400 transition-colors">
          {previewUrl ? (
            <div className="relative w-full h-48 bg-gray-50 rounded-xl overflow-hidden border border-gray-200">
              <img src={previewUrl} alt="Flowchart Preview" className="w-full h-full object-contain" />
            </div>
          ) : (
            <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-2xl">
              🖼️
            </div>
          )}

          <div>
            <label className="cursor-pointer inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white font-semibold text-sm rounded-xl hover:bg-indigo-700 transition-all shadow-sm">
              <UploadCloud size={18} />
              {selectedFile ? 'Choose Different Image' : 'Select Flowchart Image'}
              <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            </label>
            <p className="text-xs text-gray-400 mt-2">Supports PNG, JPG, JPEG formats</p>
          </div>

          <div className="pt-4 border-t border-gray-100 w-full flex items-center justify-center gap-3">
            <button
              onClick={() => handleAnalyze('upload')}
              disabled={!selectedFile || loading}
              className="px-5 py-2 bg-gray-900 text-white rounded-xl text-xs font-bold hover:bg-gray-800 disabled:opacity-50 transition-all"
            >
              {loading ? 'Processing CV & OCR...' : 'Run Vision AI Analysis'}
            </button>
            <button
              onClick={() => handleAnalyze('sample')}
              disabled={loading}
              className="px-4 py-2 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-xl text-xs font-bold hover:bg-indigo-100 transition-all"
            >
              Try Sample Flowchart
            </button>
          </div>
        </div>

        {/* Results Preview */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 flex flex-col justify-between shadow-xs">
          <div>
            <h3 className="font-bold text-gray-800 text-base mb-2 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-500" />
              Vision & OCR Detection Results
            </h3>

            {error && (
              <div className="p-3 bg-red-50 text-red-600 text-xs rounded-xl font-medium mb-4">
                {error}
              </div>
            )}

            {!analysisResult ? (
              <div className="py-12 text-center text-gray-400 text-xs">
                Upload an image or try sample flowchart to view detected blocks & connectors.
              </div>
            ) : (
              <div className="space-y-4">
                {analysisResult.overlay_image && (
                  <div className="rounded-xl overflow-hidden border border-gray-100">
                    <img
                      src={`data:image/png;base64,${analysisResult.overlay_image}`}
                      alt="Overlay"
                      className="w-full h-44 object-contain bg-gray-900"
                    />
                  </div>
                )}
                <div className="bg-gray-50 rounded-xl p-3 text-xs space-y-1 font-mono text-gray-700">
                  <p className="font-bold text-gray-800 font-sans">
                    Detected {analysisResult.blocks?.length || 0} symbols & {analysisResult.connections?.length || 0} connections:
                  </p>
                  {analysisResult.blocks?.map((b: any, idx: number) => (
                    <div key={idx} className="flex justify-between border-b border-gray-200/50 py-0.5">
                      <span className="font-semibold text-indigo-600">[{b.type}]</span>
                      <span>"{b.text || 'No text'}"</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {analysisResult && (
            <button
              onClick={handleImportToCanvas}
              className="mt-6 w-full flex items-center justify-center gap-2 py-3 bg-green-600 text-white font-bold text-sm rounded-xl hover:bg-green-700 transition-all shadow-sm"
            >
              <CheckCircle2 size={18} />
              Import Detected Flowchart to Canvas
              <ArrowRight size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
