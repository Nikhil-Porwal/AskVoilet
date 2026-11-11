import React from "react";
import { FileText, Trash2 } from "lucide-react";

const Sidebar = ({ collections, selectedCollection, onSelect, onDelete }) => (
  <aside className="app-sidebar bg-white border-r border-slate-200 flex flex-col">
    <div className="p-5 border-b border-slate-200">
      <h2 className="text-base font-semibold text-slate-900">Your collections</h2>
      <p className="text-sm text-gray-500 mt-1">{collections.length} total</p>
    </div>

    <div className="flex-1 overflow-y-auto p-3 space-y-2">
      {collections.length === 0 ? (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No collections yet</p>
          <p className="text-gray-400 text-xs mt-1">Upload PDFs to get started</p>
        </div>
      ) : (
        collections.map((collection) => (
          <div
            key={collection.id}
            onClick={() => onSelect(collection)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedCollection?.id === collection.id
                ? "border-purple-500 bg-purple-50"
                : "border-slate-200 hover:border-purple-300 bg-white"
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <h3 className="font-medium text-slate-900 mb-1 truncate">{collection.collection_name}</h3>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span className="px-2 py-1 bg-slate-100 rounded-md">{collection.llm_model || "Gemini"}</span>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(collection.id);
                }}
                className="p-1 hover:bg-red-100 rounded transition-colors"
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  </aside>
);

export default Sidebar;
