import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#050505] text-slate-300 font-mono text-xs tracking-widest">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-blue-500 pulse-dot" />
          INITIALIZING SECURITY CONSOLE
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}
