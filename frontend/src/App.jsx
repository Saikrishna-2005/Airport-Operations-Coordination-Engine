import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from "react-router-dom";

import { useEffect, useState } from "react";

import api from "./api";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Flights from "./pages/Flights";
import Weather from "./pages/Weather";
import Resources from "./pages/Resources";
import Staff from "./pages/Staff";
import AIDecisions from "./pages/AIDecisions";
import AgentMonitoring from "./pages/AgentMonitoring";
import ResourceManagement from "./pages/ResourceManagement";
import UserManagement from "./pages/UserManagement";

// NEW: Staff Assignment History
import StaffAssignmentHistory from "./components/StaffAssignmentHistory";

// ============================================================
// PROTECTED DASHBOARD LAYOUT
// ============================================================

function ProtectedLayout() {
  const navigate = useNavigate();

  const [token, setToken] = useState(() =>
    sessionStorage.getItem("airport-access-token")
  );

  const [currentUser, setCurrentUser] = useState(null);
  const [checkingRole, setCheckingRole] = useState(true);

  // ==========================================================
  // VERIFY AUTHENTICATED USER AND ROLE
  // ==========================================================

  useEffect(() => {
    let active = true;

    async function verifyUser() {
      setCheckingRole(true);

      if (!token) {
        setCurrentUser(null);
        setCheckingRole(false);
        return;
      }

      try {
        const response = await api.get("/auth/me");

        if (active) {
          setCurrentUser(response.data);
        }
      } catch (error) {
        if (active) {
          console.error(
            "Unable to verify authenticated user:",
            error
          );

          setCurrentUser(null);
        }
      } finally {
        if (active) {
          setCheckingRole(false);
        }
      }
    }

    verifyUser();

    return () => {
      active = false;
    };
  }, [token]);

  // ==========================================================
  // LOGIN / LOGOUT EVENT HANDLING
  // ==========================================================

  useEffect(() => {
    function handleLogout() {
      setToken(null);
      setCurrentUser(null);

      navigate("/login", { replace: true });
    }

    function handleLogin() {
      const currentToken = sessionStorage.getItem(
        "airport-access-token"
      );

      setToken(currentToken);
    }

    function handleStorageChange() {
      const currentToken = sessionStorage.getItem(
        "airport-access-token"
      );

      setToken(currentToken);

      if (!currentToken) {
        setCurrentUser(null);
        navigate("/login", { replace: true });
      }
    }

    window.addEventListener("airport-logout", handleLogout);
    window.addEventListener("airport-login", handleLogin);
    window.addEventListener("storage", handleStorageChange);

    return () => {
      window.removeEventListener(
        "airport-logout",
        handleLogout
      );

      window.removeEventListener(
        "airport-login",
        handleLogin
      );

      window.removeEventListener(
        "storage",
        handleStorageChange
      );
    };
  }, [navigate]);

  // ==========================================================
  // AUTHENTICATION PROTECTION
  // ==========================================================

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (checkingRole) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="text-center">
          <div className="mb-4 text-2xl font-bold text-cyan-400">
            Airport Operations
          </div>

          <p className="text-sm text-slate-400">
            Verifying user permissions...
          </p>
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white">
        <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 text-center">
          <h2 className="text-xl font-semibold text-red-400">
            Authentication Failed
          </h2>

          <p className="mt-3 text-sm text-slate-400">
            Unable to verify your account. Please sign in again.
          </p>

          <button
            type="button"
            onClick={() => {
              sessionStorage.removeItem(
                "airport-access-token"
              );

              sessionStorage.removeItem(
                "airport-demo-login"
              );

              window.dispatchEvent(
                new Event("airport-logout")
              );
            }}
            className="mt-5 rounded-lg bg-cyan-400 px-5 py-2 font-semibold text-slate-950 hover:bg-cyan-300"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  // ==========================================================
  // ROLE-BASED ACCESS
  // ==========================================================

  const isAdmin = currentUser.role === "admin";

  // ==========================================================
  // DASHBOARD LAYOUT
  // ==========================================================

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="flex">
        <Sidebar userRole={currentUser.role} />

        <div className="min-w-0 flex-1">
          <Header />

          <main className="p-6">
            <Routes>
              <Route
                path="/"
                element={<Dashboard />}
              />

              <Route
                path="/flights"
                element={<Flights />}
              />

              <Route
                path="/weather"
                element={<Weather />}
              />

              <Route
                path="/resources"
                element={<Resources />}
              />

              <Route
                path="/staff"
                element={
                  <Staff userRole={currentUser.role} />
                }
              />

              {/* NEW: STAFF ASSIGNMENT HISTORY */}

              <Route
                path="/staff/history"
                element={<StaffAssignmentHistory />}
              />

              <Route
                path="/ai-decisions"
                element={<AIDecisions />}
              />

              <Route
                path="/agent-monitoring"
                element={<AgentMonitoring />}
              />

              <Route
                path="/resource-management"
                element={<ResourceManagement />}
              />

              {/* ADMIN-ONLY USER MANAGEMENT */}

              <Route
                path="/users"
                element={
                  isAdmin ? (
                    <UserManagement />
                  ) : (
                    <Navigate to="/" replace />
                  )
                }
              />

              {/* FALLBACK ROUTE */}

              <Route
                path="*"
                element={<Navigate to="/" replace />}
              />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// LOGIN ROUTE
// ============================================================

function LoginRoute() {
  const [token, setToken] = useState(() =>
    sessionStorage.getItem("airport-access-token")
  );

  useEffect(() => {
    function handleLogout() {
      setToken(null);
    }

    function handleLogin() {
      setToken(
        sessionStorage.getItem("airport-access-token")
      );
    }

    window.addEventListener(
      "airport-logout",
      handleLogout
    );

    window.addEventListener(
      "airport-login",
      handleLogin
    );

    return () => {
      window.removeEventListener(
        "airport-logout",
        handleLogout
      );

      window.removeEventListener(
        "airport-login",
        handleLogin
      );
    };
  }, []);

  return token ? (
    <Navigate to="/" replace />
  ) : (
    <Login />
  );
}

// ============================================================
// MAIN APPLICATION
// ============================================================

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={<LoginRoute />}
        />

        <Route
          path="/*"
          element={<ProtectedLayout />}
        />
      </Routes>
    </BrowserRouter>
  );
}