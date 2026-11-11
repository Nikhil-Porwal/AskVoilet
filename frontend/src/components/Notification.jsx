import React from "react";
import { AlertCircle, CheckCircle } from "lucide-react";

const Notification = ({ notification }) => {
  if (!notification) return null;

  return (
    <div
      className={`fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-slide-in ${
        notification.type === "error" ? "bg-red-500" : "bg-green-500"
      } text-white`}
    >
      {notification.type === "error" ? (
        <AlertCircle className="w-5 h-5" />
      ) : (
        <CheckCircle className="w-5 h-5" />
      )}
      {notification.message}
    </div>
  );
};

export default Notification;
