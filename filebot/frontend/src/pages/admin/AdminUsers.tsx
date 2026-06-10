import React, { useState, useEffect } from 'react';
import userService, { User, UserUpdate } from '../../services/user.service';
import { showToast } from '../../components/common/ToastNotification';

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);

  // Edit form state
  const [editFullName, setEditFullName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editIsActive, setEditIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await userService.getUsers();
      setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError('Failed to load user list. Check your connection or try re-login.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  // Open edit modal
  const handleEdit = (user: User) => {
    setEditingUser(user);
    setEditFullName(user.full_name || '');
    setEditEmail(user.email);
    setEditPassword('');
    setEditIsActive(user.is_active);
    setShowEditModal(true);
  };

  // Save edit
  const handleSaveEdit = async () => {
    if (!editingUser) return;

    try {
      setSaving(true);
      const updateData: UserUpdate = {
        full_name: editFullName || undefined,
        email: editEmail,
        is_active: editIsActive,
      };
      if (editPassword) {
        updateData.password = editPassword;
      }

      const updated = await userService.updateUser(editingUser.id, updateData);
      setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
      setShowEditModal(false);
      setEditingUser(null);
      showToast(`User ${updated.username} updated`, 'success');
    } catch (err) {
      console.error('Failed to update user:', err);
      showToast('Failed to update user. Please try again.', 'error');
    } finally {
      setSaving(false);
    }
  };

  // Delete user
  const handleDelete = async (user: User) => {
    const confirmed = await window.wetYesOrNo(
      `Are you sure you want to delete user "${user.username}"? This action cannot be undone.`
    );
    if (!confirmed) return;

    try {
      await userService.deleteUser(user.id);
      setUsers(prev => prev.filter(u => u.id !== user.id));
      showToast(`User ${user.username} deleted`, 'success');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Unknown error';
      showToast(`Delete failed: ${detail}`, 'error');
    }
  };

  // Toggle active status
  const handleToggleActive = async (user: User) => {
    try {
      const action = user.is_active ? 'deactivate' : 'activate';
      const confirmed = await window.wetYesOrNo(`Are you sure you want to ${action} user "${user.username}"?`);
      if (!confirmed) return;

      const updated = await userService.toggleActive(user.id);
      setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
      showToast(`User ${updated.username} ${updated.is_active ? 'activated' : 'deactivated'}`, 'success');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Unknown error';
      showToast(`Operation failed: ${detail}`, 'error');
    }
  };

  const closeModal = () => {
    setShowEditModal(false);
    setEditingUser(null);
  };

  // Format date
  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-CA', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">User Management</h1>
        </div>
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading users...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">User Management</h1>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h3 className="text-lg font-medium text-red-800 mb-2">Load Failed</h3>
          <p className="text-red-700 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">User Management</h1>
        <span className="text-sm text-gray-500">{users.length} user{users.length !== 1 ? 's' : ''}</span>
      </div>

      {users.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
          <h3 className="text-lg font-medium text-yellow-800 mb-2">No Users</h3>
          <p className="text-yellow-700">No users have been registered yet.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Username</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Full Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                          <span className="text-sm font-medium text-blue-600">
                            {user.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="ml-3">
                          <div className="text-sm font-medium text-gray-900">{user.username}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.full_name || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_superuser ? (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                          Admin
                        </span>
                      ) : (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                          {user.role || 'User'}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          user.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-2">
                        <button
                          onClick={() => handleToggleActive(user)}
                          className={`px-3 py-1 rounded-full text-xs focus:outline-none focus:ring-2 focus:ring-offset-1 ${
                            user.is_active
                              ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200 focus:ring-yellow-300'
                              : 'bg-green-100 text-green-800 hover:bg-green-200 focus:ring-green-300'
                          }`}
                        >
                          {user.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button
                          onClick={() => handleEdit(user)}
                          className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(user)}
                          className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-300"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && editingUser && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={closeModal}></div>
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 z-10">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Edit User: {editingUser.username}</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={editFullName}
                    onChange={e => setEditFullName(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Full name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={editEmail}
                    onChange={e => setEditEmail(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="email@example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Change Password <span className="text-gray-400 font-normal">(leave blank to keep current)</span>
                  </label>
                  <input
                    type="password"
                    value={editPassword}
                    onChange={e => setEditPassword(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="New password"
                  />
                </div>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="edit-is-active"
                    checked={editIsActive}
                    onChange={e => setEditIsActive(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="edit-is-active" className="ml-2 text-sm text-gray-700">Account Active</label>
                </div>
              </div>

              <div className="mt-6 flex justify-end space-x-3">
                <button
                  onClick={closeModal}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-300"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={saving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsers;
