import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plane, LockKeyhole, Mail, UserPlus } from "lucide-react";
import api from "../api";

export default function Login() {
  const [isSignup, setIsSignup] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  // ==========================================================
  // LOGIN
  // ==========================================================

  async function handleLogin(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!username.trim() || !password.trim()) {
      setError("Please enter your username and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await api.post("/auth/login", {
        username: username.trim(),
        password,
      });

      const token = response.data?.access_token;

      if (typeof token !== "string" || !token.trim()) {
        throw new Error(
          "Login succeeded, but no valid access token was returned."
        );
      }

      // Preserve existing JWT storage.
      sessionStorage.setItem("airport-access-token", token);

      if (!sessionStorage.getItem("airport-access-token")) {
        throw new Error("Unable to store the authentication token.");
      }

      // Remove old mock-login flag.
      sessionStorage.removeItem("airport-demo-login");

      // Notify the application.
      window.dispatchEvent(new Event("airport-login"));

      // Navigate to dashboard.
      navigate("/", { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : err.message || "Login failed. Please check your credentials."
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // SIGNUP
  // ==========================================================

  async function handleSignup(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (username.trim().length < 3) {
      setError("Username must contain at least 3 characters.");
      return;
    }

    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const response = await api.post("/auth/signup", {
        username: username.trim(),
        password,
        confirm_password: confirmPassword,
      });

      if (response.status !== 201) {
        throw new Error("Account registration was not completed.");
      }

      // Signup does not automatically authenticate the user.
      setIsSignup(false);
      setPassword("");
      setConfirmPassword("");

      setSuccess(
        "Account created successfully! Please sign in with your credentials."
      );
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "Registration failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // SWITCH BETWEEN LOGIN AND SIGNUP
  // ==========================================================

  function switchMode() {
    setIsSignup((previous) => !previous);
    setError("");
    setSuccess("");
    setPassword("");
    setConfirmPassword("");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-2xl">

        <div className="mb-6 flex justify-center">
          <div className="rounded-2xl bg-cyan-400/10 p-4">
            <Plane size={36} className="text-cyan-400" />
          </div>
        </div>

        <h1 className="text-center text-2xl font-bold">
          Airport Operations
        </h1>

        <p className="mt-2 text-center text-sm text-slate-400">
          Coordination Engine
        </p>

        <h2 className="mt-6 text-center text-xl font-semibold">
          {isSignup ? "Create Account" : "Sign In"}
        </h2>

        <form
          onSubmit={isSignup ? handleSignup : handleLogin}
          className="mt-6 space-y-5"
        >

          {/* USERNAME */}

          <div>
            <label
              htmlFor="username"
              className="mb-2 block text-sm text-slate-300"
            >
              Username
            </label>

            <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-950 px-3">
              <Mail size={18} className="text-slate-400" />

              <input
                id="username"
                type="text"
                value={username}
                onChange={(event) => {
                  setUsername(event.target.value);
                  setError("");
                }}
                placeholder="Enter your username"
                autoComplete="username"
                minLength={isSignup ? 3 : 1}
                maxLength={100}
                className="w-full bg-transparent py-3 text-white outline-none"
                required
              />
            </div>
          </div>

          {/* PASSWORD */}

          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm text-slate-300"
            >
              Password
            </label>

            <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-950 px-3">
              <LockKeyhole size={18} className="text-slate-400" />

              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setError("");
                }}
                placeholder="Enter your password"
                autoComplete={
                  isSignup ? "new-password" : "current-password"
                }
                minLength={isSignup ? 8 : 1}
                maxLength={128}
                className="w-full bg-transparent py-3 text-white outline-none"
                required
              />
            </div>
          </div>

          {/* CONFIRM PASSWORD — SIGNUP ONLY */}

          {isSignup && (
            <div>
              <label
                htmlFor="confirmPassword"
                className="mb-2 block text-sm text-slate-300"
              >
                Confirm Password
              </label>

              <div className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-950 px-3">
                <LockKeyhole size={18} className="text-slate-400" />

                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => {
                    setConfirmPassword(event.target.value);
                    setError("");
                  }}
                  placeholder="Confirm your password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  className="w-full bg-transparent py-3 text-white outline-none"
                  required
                />
              </div>
            </div>
          )}

          {/* ERROR MESSAGE */}

          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}

          {/* SUCCESS MESSAGE */}

          {success && (
            <p role="status" className="text-sm text-green-400">
              {success}
            </p>
          )}

          {/* SUBMIT BUTTON */}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-cyan-400 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading
              ? isSignup
                ? "Creating Account..."
                : "Signing In..."
              : isSignup
              ? "Create Account"
              : "Sign In"}
          </button>
        </form>

        {/* SWITCH BETWEEN LOGIN AND SIGNUP */}

        <div className="mt-6 text-center">
          <p className="text-sm text-slate-400">
            {isSignup
              ? "Already have an account?"
              : "Don't have an account?"}
          </p>

          <button
            type="button"
            onClick={switchMode}
            disabled={loading}
            className="mt-2 flex items-center justify-center gap-2 mx-auto font-semibold text-cyan-400 transition hover:text-cyan-300 disabled:opacity-60"
          >
            {isSignup && <UserPlus size={16} />}

            {isSignup ? "Sign In" : "Create an Account"}
          </button>
        </div>

        <p className="mt-6 text-center text-xs text-slate-500">
          Airport Operations Coordination Engine
        </p>
      </div>
    </div>
  );
}