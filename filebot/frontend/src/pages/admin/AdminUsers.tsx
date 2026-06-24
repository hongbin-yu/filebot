import React, { useState, useEffect } from 'react';
import userService, { User, UserUpdate } from '../../services/user.service';
import institutionService, { Institution } from '../../services/institution.service';
import groupService, { Group } from '../../services/group.service';
import { showToast } from '../../components/common/ToastNotification';

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [institutionFilter, setInstitutionFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Edit form state
  const [editFullName, setEditFullName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editIsActive, setEditIsActive] = useState(true);
  const [editInstitutionId, setEditInstitutionId] = useState('');
  const [saving, setSaving] = useState(false);
  const [editUserGroupIds, setEditUserGroupIds] = useState<Set<string>>(new Set());
  const [availableGroups, setAvailableGroups] = useState<Group[]>([]);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [editGroupSaving, setEditGroupSaving] = useState(false);

  // Create form state
  const [createUsername, setCreateUsername] = useState('');
  const [createFullName, setCreateFullName] = useState('');
  const [createEmail, setCreateEmail] = useState('');
  const [createPassword, setCreatePassword] = useState('');
  const [createRole, setCreateRole] = useState('user');
  const [createInstitutionId, setCreateInstitutionId] = useState('');
  const [creating, setCreating] = useState(false);

  // Get institution name by id
  const getInstitutionName = (institutionId?: string): string => {
    if (!institutionId) return '-';
    const inst = institutions.find(i => i.id === institutionId);
    return inst ? inst.name : institutionId;
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [userData, instData] = await Promise.all([
        userService.getUsers(),
        institutionService.getAllInstitutions(),
      ]);
      setUsers(userData);
      setInstitutions(instData);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load user list. Check your connection or try re-login.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Reload groups when institution changes in edit modal
  const loadGroupsForInstitution = async (institutionId?: string) => {
    setGroupsLoading(true);
    try {
      const groups = await groupService.list(institutionId || undefined);
      setAvailableGroups(groups);
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setGroupsLoading(false);
    }
  };

  // Filter users by institution
  const filteredUsers = institutionFilter
    ? users.filter(u => u.institution_id === institutionFilter)
    : users;

  // Open edit modal
  const handleEdit = async (user: User) => {
    setEditingUser(user);
    setEditFullName(user.full_name || '');
    setEditEmail(user.email);
    setEditPassword('');
    setEditIsActive(user.is_active);
    setEditInstitutionId(user.institution_id || '');
    setEditUserGroupIds(new Set());
    setShowEditModal(true);

    // Load groups for this user
    setGroupsLoading(true);
    try {
      const [groups, userGroups] = await Promise.all([
        groupService.list(user.institution_id),
        userService.getUserGroups(user.id),
      ]);
      setAvailableGroups(groups);
      setEditUserGroupIds(new Set(userGroups.map(g => g.id)));
    } catch (err) {
      console.error('Failed to load groups:', err);
    } finally {
      setGroupsLoading(false);
    }
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
        institution_id: editInstitutionId || undefined,
      };
      if (editPassword) {
        updateData.password = editPassword;
      }

      const updated = await userService.updateUser(editingUser.id, updateData);

      // Sync group assignments
      setEditGroupSaving(true);
      try {
        const currentGroups = await userService.getUserGroups(editingUser.id);
        const currentIds = new Set(currentGroups.map(g => g.id));

        // Add to newly selected groups
        for (const gid of editUserGroupIds) {
          if (!currentIds.has(gid)) {
            await groupService.addMember(gid, { user_id: editingUser.id, role: 'member' });
          }
        }
        // Remove from unselected groups
        for (const gid of currentIds) {
          if (!editUserGroupIds.has(gid)) {
            await groupService.removeMember(gid, editingUser.id);
          }
        }
      } catch (err) {
        console.error('Failed to sync group assignments:', err);
        showToast('User updated but group sync may be incomplete.', 'error');
      } finally {
        setEditGroupSaving(false);
      }

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

  // Create new user
  const handleCreate = async () => {
    if (!createUsername || !createEmail || !createPassword) {
      showToast('Please fill in username, email, and password.', 'error');
      return;
    }
    if (createPassword.length < 6) {
      showToast('Password must be at least 6 characters.', 'error');
      return;
    }

    try {
      setCreating(true);
      const newUser = await userService.createUser({
        username: createUsername,
        email: createEmail,
        password: createPassword,
        full_name: createFullName || undefined,
        role: createRole,
        institution_id: createInstitutionId || undefined,
      });
      setUsers(prev => [...prev, newUser]);
      setShowCreateModal(false);
      resetCreateForm();
      showToast(`User ${newUser.username} created`, 'success');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Unknown error';
      showToast(`Create failed: ${detail}`, 'error');
    } finally {
      setCreating(false);
    }
  };

  const resetCreateForm = () => {
    setCreateUsername('');
    setCreateFullName('');
    setCreateEmail('');
    setCreatePassword('');
    setCreateRole('user');
    setCreateInstitutionId('');
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

  const closeEditModal = () => {
    setShowEditModal(false);
    setEditingUser(null);
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    resetCreateForm();
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
      <div style={{padding:24}}>
        <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:24}}>
          <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>User Management</h1>
        </div>
        <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
          <div>
            <div className="fb-spinner" style={{height:48,width:48,borderWidth:2,borderColor:"#2563eb",borderRadius:"50%"}}></div>
            <p style={{marginTop:16}}>Loading users...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{padding:24}}>
        <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:24}}>
          <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>User Management</h1>
        </div>
        <div style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:24}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#991b1b",marginBottom:8}}>Load Failed</h3>
          <p style={{color:"#b91c1c",marginBottom:16}}>{error}</p>
          <button onClick={() => window.location.reload()} className="btn btn-danger">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{padding:24}}>
      {/* Header: title + Add User button */}
      <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
        <h1 style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}>User Management</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,background:"#2563eb",color:"#ffffff",borderRadius:6,fontSize:"0.875rem",fontWeight:500}}
        >
          + Add User
        </button>
      </div>

      {/* Toolbar: institution filter + count */}
      <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}>
        <div className="fb-d-flex fb-align-center" style={{gap:12}}>
          <label style={{fontSize:"0.875rem",fontWeight:500,color:"#374151"}}>Institution:</label>
          <select
            value={institutionFilter}
            onChange={e => setInstitutionFilter(e.target.value)}
            style={{border:"1px solid #d1d5db",borderRadius:6,padding:"6px 12px",fontSize:"0.875rem",background:"#ffffff",minWidth:200,height:34}}
          >
            <option value="">All Institutions</option>
            {institutions.map(inst => (
              <option key={inst.id} value={inst.id}>{inst.name}</option>
            ))}
          </select>
        </div>
        <span style={{fontSize:"0.875rem",color:"#6b7280"}}>
          {filteredUsers.length} user{filteredUsers.length !== 1 ? 's' : ''}
          {institutionFilter && ` (filtered)`}
        </span>
      </div>

      {filteredUsers.length === 0 ? (
        <div style={{background:"#fefce8",border:"1px solid #fef08a",borderRadius:8,padding:32}}>
          <h3 style={{fontSize:"1.125rem",fontWeight:500,color:"#854d0e",marginBottom:8}}>No Users</h3>
          <p style={{color:"#a16207"}}>
            {institutionFilter ? 'No users in the selected institution.' : 'No users have been registered yet.'}
          </p>
        </div>
      ) : (
        <div className="panel panel-default" style={{overflow:"hidden"}}>
          <div style={{overflowX:"auto"}}>
            <table className="fb-divide-y" style={{minWidth:"100%", "--divide-color":"#e5e7eb"}}>
              <thead style={{background:"#f9fafb"}}>
                <tr>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Username</th>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Full Name</th>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Email</th>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Institution</th>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Role</th>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Status</th>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Created</th>
                  <th style={{paddingLeft:24,paddingTop:12,fontSize:"0.75rem",fontWeight:500,textTransform:"uppercase",letterSpacing:"0.05em"}}>Actions</th>
                </tr>
              </thead>
              <tbody className="table">
                {filteredUsers.map(user => (
                  <tr key={user.id} className="fb-hover-btn">
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap"}}>
                      <div className="fb-d-flex fb-align-center">
                        <div className="fb-align-center fb-justify-center" style={{flexShrink:0,height:32,width:32,borderRadius:"50%",background:"#dbeafe",display:"flex"}}>
                          <span style={{fontSize:"0.875rem",fontWeight:500,color:"#2563eb"}}>
                            {user.username.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div style={{marginLeft:12}}>
                          <div className="fb-label" style={{fontSize:"0.875rem",color:"#111827"}}>{user.username}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap",fontSize:"0.875rem"}}>
                      {user.full_name || '-'}
                    </td>
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap",fontSize:"0.875rem"}}>
                      {user.email}
                    </td>
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap",fontSize:"0.875rem",color:"#374151"}}>
                      {getInstitutionName(user.institution_id)}
                    </td>
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap"}}>
                      {user.is_superuser ? (
                        <span style={{paddingLeft:8,paddingRight:8,display:"inline-flex",fontSize:"0.75rem",lineHeight:"1.25rem",fontWeight:600,borderRadius:"50%",background:"#f3e8ff",color:"#6b21a8"}}>
                          Super Admin
                        </span>
                      ) : (
                        <span style={{paddingLeft:8,paddingRight:8,display:"inline-flex",fontSize:"0.75rem",lineHeight:"1.25rem",fontWeight:600,borderRadius:"50%",background:"#f3f4f6",color:"#1f2937"}}>
                          {user.role || 'User'}
                        </span>
                      )}
                    </td>
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap"}}>
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap",fontSize:"0.875rem"}}>
                      {formatDate(user.created_at)}
                    </td>
                    <td style={{paddingLeft:24,paddingTop:16,whiteSpace:"nowrap",fontSize:"0.875rem",fontWeight:500}}>
                      <div className="fb-justify-end" style={{display:"flex",columnGap:8}}>
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
                        <button onClick={() => handleEdit(user)} style={{paddingLeft:12,paddingTop:4,background:"#dbeafe",color:"#1e40af",borderRadius:"50%",fontSize:"0.75rem"}}>
                          Edit
                        </button>
                        <button onClick={() => handleDelete(user)} style={{paddingLeft:12,paddingTop:4,background:"#fee2e2",color:"#991b1b",borderRadius:"50%",fontSize:"0.75rem"}}>
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
        <div className="fb-modal-backdrop">
          <div className="fb-modal-content" style={{maxWidth:448,width:"100%",background:"#ffffff",borderRadius:8,padding:24}}>
            <h3 style={{fontSize:"1.125rem",fontWeight:600,color:"#111827",marginBottom:16}}>Edit User: {editingUser.username}</h3>
            <div className="fb-space-y" style={{gap:16}}>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Full Name</label>
                <input type="text" value={editFullName} onChange={e => setEditFullName(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem"}} placeholder="Full name" />
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Email</label>
                <input type="email" value={editEmail} onChange={e => setEditEmail(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem"}} placeholder="email@example.com" />
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Institution</label>
                <select value={editInstitutionId} onChange={e => { setEditInstitutionId(e.target.value); setEditUserGroupIds(new Set()); loadGroupsForInstitution(e.target.value); }}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem",background:"#ffffff"}}>
                  <option value="">None</option>
                  {institutions.map(inst => (
                    <option key={inst.id} value={inst.id}>{inst.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>
                  Change Password <span style={{color:"#9ca3af",fontWeight:400}}>(leave blank to keep current)</span>
                </label>
                <input type="password" value={editPassword} onChange={e => setEditPassword(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem"}} placeholder="New password" />
              </div>
              {/* Groups assignment */}
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:8}}>Groups</label>
                {groupsLoading ? (
                  <span style={{fontSize:"0.875rem",color:"#9ca3af"}}>Loading groups...</span>
                ) : availableGroups.length === 0 ? (
                  <span style={{fontSize:"0.875rem",color:"#9ca3af"}}>No groups available</span>
                ) : (
                  <div style={{maxHeight:160,overflowY:"auto",border:"1px solid",borderColor:"#e5e7eb",borderRadius:6,padding:8}}>
                    {availableGroups.map(group => (
                      <label key={group.id} className="fb-d-flex fb-align-center" style={{paddingTop:4,paddingBottom:4,cursor:"pointer"}}>
                        <input
                          type="checkbox"
                          checked={editUserGroupIds.has(group.id)}
                          onChange={e => {
                            const next = new Set(editUserGroupIds);
                            if (e.target.checked) next.add(group.id);
                            else next.delete(group.id);
                            setEditUserGroupIds(next);
                          }}
                          style={{height:16,width:16,color:"#2563eb",borderColor:"#d1d5db",borderRadius:4}}
                        />
                        <span style={{marginLeft:8,fontSize:"0.875rem",color:"#374151"}}>{group.name}</span>
                        {group.institution_name && <span style={{marginLeft:6,fontSize:"0.75rem",color:"#9ca3af"}}>({group.institution_name})</span>}
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <div className="fb-d-flex fb-align-center">
                <input type="checkbox" id="edit-is-active" checked={editIsActive} onChange={e => setEditIsActive(e.target.checked)}
                  style={{height:16,width:16,color:"#2563eb",borderColor:"#d1d5db",borderRadius:4}} />
                <label htmlFor="edit-is-active" style={{marginLeft:8,fontSize:"0.875rem",color:"#374151"}}>Account Active</label>
              </div>
            </div>
            <div className="fb-justify-end" style={{marginTop:24,display:"flex",columnGap:12}}>
              <button onClick={closeEditModal} style={{paddingLeft:16,paddingTop:8,background:"#f3f4f6",color:"#374151",borderRadius:6,fontSize:"0.875rem"}}>Cancel</button>
              <button onClick={handleSaveEdit} disabled={saving || editGroupSaving}
                style={{paddingLeft:16,paddingTop:8,background:"#2563eb",color:"#ffffff",borderRadius:6,fontSize:"0.875rem"}}>
                {saving || editGroupSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fb-modal-backdrop">
          <div className="fb-modal-content" style={{maxWidth:448,width:"100%",background:"#ffffff",borderRadius:8,padding:24}}>
            <h3 style={{fontSize:"1.125rem",fontWeight:600,color:"#111827",marginBottom:16}}>Add New User</h3>
            <div className="fb-space-y" style={{gap:16}}>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Username *</label>
                <input type="text" value={createUsername} onChange={e => setCreateUsername(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem"}} placeholder="username" />
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Full Name</label>
                <input type="text" value={createFullName} onChange={e => setCreateFullName(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem"}} placeholder="Full name" />
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Email *</label>
                <input type="email" value={createEmail} onChange={e => setCreateEmail(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem"}} placeholder="email@example.com" />
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Password *</label>
                <input type="password" value={createPassword} onChange={e => setCreatePassword(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem"}} placeholder="Min 6 characters" />
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Role</label>
                <select value={createRole} onChange={e => setCreateRole(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem",background:"#ffffff"}}>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <label className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}>Institution</label>
                <select value={createInstitutionId} onChange={e => setCreateInstitutionId(e.target.value)}
                  style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:6,paddingLeft:12,paddingTop:8,fontSize:"0.875rem",background:"#ffffff"}}>
                  <option value="">None</option>
                  {institutions.map(inst => (
                    <option key={inst.id} value={inst.id}>{inst.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="fb-justify-end" style={{marginTop:24,display:"flex",columnGap:12}}>
              <button onClick={closeCreateModal} style={{paddingLeft:16,paddingTop:8,background:"#f3f4f6",color:"#374151",borderRadius:6,fontSize:"0.875rem"}}>Cancel</button>
              <button onClick={handleCreate} disabled={creating}
                style={{paddingLeft:16,paddingTop:8,background:"#2563eb",color:"#ffffff",borderRadius:6,fontSize:"0.875rem"}}>
                {creating ? 'Creating...' : 'Create User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsers;
