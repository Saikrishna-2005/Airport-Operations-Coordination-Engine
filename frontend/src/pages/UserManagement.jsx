import { useCallback, useEffect, useState } from "react";
import { Users, RefreshCw, ShieldCheck } from "lucide-react";
import api from "../api";

const AVAILABLE_ROLES = ["admin", "pilot", "operator"];

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [selectedRoles, setSelectedRoles] = useState({});
  const [loading, setLoading] = useState(true);
  const [updatingUserId, setUpdatingUserId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/admin/users");

      const userList = response.data?.users;

      if (!Array.isArray(userList)) {
        throw new Error("Invalid response from the server.");
      }

      setUsers(userList);

      const initialRoles = {};

      userList.forEach((user) => {
        initialRoles[user.user_id] = user.role;
      });

      setSelectedRoles(initialRoles);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to load registered users."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  function handleRoleSelection(userId, role) {
    setSelectedRoles((previous) => ({
      ...previous,
      [userId]: role,
    }));

    setError("");
    setSuccess("");
  }

  async function handleUpdateRole(user) {
    const newRole = selectedRoles[user.user_id];

    if (!AVAILABLE_ROLES.includes(newRole)) {
      setError("Please select a valid role.");
      return;
    }

    if (newRole === user.role) {
      return;
    }

    const confirmed = window.confirm(
      `Change ${user.username}'s role from ${user.role} to ${newRole}?`
    );

    if (!confirmed) {
      return;
    }

    setUpdatingUserId(user.user_id);
    setError("");
    setSuccess("");

    try {
      await api.patch(
        `/admin/users/${encodeURIComponent(user.user_id)}/role`,
        { role: newRole }
      );

      setSuccess(
        `${user.username}'s role was updated to ${newRole}.`
      );

      await fetchUsers();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to update user role."
      );
    } finally {
      setUpdatingUserId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-white">
            <Users className="text-cyan-400" size={28} />
            User Management
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Manage registered users and assign system roles.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchUsers}
          disabled={loading || updatingUserId !== null}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-4">
        <div className="flex items-center gap-2 text-cyan-300">
          <ShieldCheck size={18} />
          <span className="font-semibold">
            Administrator Access
          </span>
        </div>

        <p className="mt-2 text-sm text-slate-400">
          Only authorized administrators can modify user roles.
          New registrations receive the Operator role by default.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
        >
          {typeof error === "string"
            ? error
            : "An unexpected error occurred."}
        </div>
      )}

      {success && (
        <div
          role="status"
          className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300"
        >
          {success}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-700 bg-slate-900">
        <div className="border-b border-slate-700 px-6 py-4">
          <h2 className="text-lg font-semibold">
            Registered Users
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Total Users: {users.length}
          </p>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400">
            Loading registered users...
          </div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            No registered users found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="bg-slate-800 text-slate-300">
                <tr>
                  <th className="px-5 py-4">Username</th>
                  <th className="px-5 py-4">User ID</th>
                  <th className="px-5 py-4">Current Role</th>
                  <th className="px-5 py-4">Assign Role</th>
                  <th className="px-5 py-4">Action</th>
                </tr>
              </thead>

              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.user_id}
                    className="border-t border-slate-700"
                  >
                    <td className="px-5 py-4 font-medium text-white">
                      {user.username}
                    </td>

                    <td className="px-5 py-4 text-slate-400">
                      {user.user_id}
                    </td>

                    <td className="px-5 py-4">
                      <span className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-semibold capitalize text-cyan-300">
                        {user.role}
                      </span>
                    </td>

                    <td className="px-5 py-4">
                      <select
                        value={
                          selectedRoles[user.user_id] ??
                          user.role
                        }
                        onChange={(event) =>
                          handleRoleSelection(
                            user.user_id,
                            event.target.value
                          )
                        }
                        disabled={updatingUserId !== null}
                        className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white outline-none focus:border-cyan-400 disabled:opacity-50"
                      >
                        {AVAILABLE_ROLES.map((role) => (
                          <option key={role} value={role}>
                            {role.charAt(0).toUpperCase() +
                              role.slice(1)}
                          </option>
                        ))}
                      </select>
                    </td>

                    <td className="px-5 py-4">
                      <button
                        type="button"
                        onClick={() => handleUpdateRole(user)}
                        disabled={
                          updatingUserId !== null ||
                          selectedRoles[user.user_id] ===
                            user.role
                        }
                        className="rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {updatingUserId === user.user_id
                          ? "Saving..."
                          : "Save Role"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}