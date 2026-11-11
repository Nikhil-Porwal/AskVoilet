import React from "react";
import { BookOpen, Upload, User, LogOut } from "lucide-react";

const Header = ({ username, onUploadClick, onLogout }) => (
  <header className="app-header bg-white/95 border-b border-slate-200 px-6 py-4 backdrop-blur">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center">
          <BookOpen className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Voilet</h1>
          <p className="app-header-subtitle text-xs text-slate-500">PDF Q&A Assistant</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={onUploadClick}
          className="bg-purple-600 text-white px-4 py-2 rounded-xl font-medium shadow-sm shadow-purple-200 hover:bg-purple-700 transition-colors flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          <span className="app-upload-label">Upload PDFs</span>
        </button>

        <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg">
          <User className="w-4 h-4 text-gray-600" />
          <span className="app-user-name text-sm font-medium text-gray-700">{username}</span>
        </div>

        <button
          onClick={onLogout}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Logout"
        >
          <LogOut className="w-5 h-5 text-gray-600" />
        </button>
      </div>
    </div>
  </header>
);

export default Header;
