import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Chip, Alert, Snackbar, Card, CardContent, Grid,
  List, ListItem, ListItemText, ListItemAvatar, Avatar, Divider,
  Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon, Group as GroupIcon, PersonAdd as PersonAddIcon, PersonRemove as PersonRemoveIcon } from '@mui/icons-material';
import groupService, { Group, GroupDetail, MemberInfo } from '../../services/group.service';
import authService from '../../services/auth.service';

const AdminGroups: React.FC = () => {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Group CRUD dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [memberDialogOpen, setMemberDialogOpen] = useState(false);
  const [addMemberDialogOpen, setAddMemberDialogOpen] = useState(false);

  const [selectedGroup, setSelectedGroup] = useState<GroupDetail | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [addMemberForm, setAddMemberForm] = useState({ user_id: '', role: 'member' });
  const [users, setUsers] = useState<{ id: string; username: string; email: string }[]>([]);

  const loadGroups = useCallback(async () => {
    try {
      setLoading(true);
      const data = await groupService.list();
      setGroups(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load groups');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    try {
      const response = await (await import('../../services/api')).default.get('/users/');
      setUsers(response.data);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => { loadGroups(); }, [loadGroups]);

  const handleCreate = async () => {
    if (!formData.name.trim()) return;
    try {
      await groupService.create({ name: formData.name, description: formData.description });
      setSuccess(`Group "${formData.name}" created`);
      setCreateDialogOpen(false);
      setFormData({ name: '', description: '' });
      loadGroups();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create group');
    }
  };

  const handleEdit = async () => {
    if (!selectedGroup) return;
    try {
      await groupService.update(selectedGroup.id, formData);
      setSuccess('Group updated');
      setEditDialogOpen(false);
      loadGroups();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update group');
    }
  };

  const handleDelete = async () => {
    if (!selectedGroup) return;
    try {
      await groupService.delete(selectedGroup.id);
      setSuccess(`Group "${selectedGroup.name}" deleted`);
      setDeleteDialogOpen(false);
      setSelectedGroup(null);
      loadGroups();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete group');
    }
  };

  const openEditDialog = async (group: Group) => {
    try {
      const detail = await groupService.get(group.id);
      setSelectedGroup(detail);
      setFormData({ name: detail.name, description: detail.description || '' });
      setEditDialogOpen(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load group details');
    }
  };

  const openMemberDialog = async (group: Group) => {
    try {
      const detail = await groupService.get(group.id);
      setSelectedGroup(detail);
      setMemberDialogOpen(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load group members');
    }
  };

  const openAddMemberDialog = () => {
    loadUsers();
    setAddMemberForm({ user_id: '', role: 'member' });
    setAddMemberDialogOpen(true);
  };

  const handleAddMember = async () => {
    if (!selectedGroup || !addMemberForm.user_id) return;
    try {
      await groupService.addMember(selectedGroup.id, addMemberForm);
      setSuccess('Member added');
      setAddMemberDialogOpen(false);
      const detail = await groupService.get(selectedGroup.id);
      setSelectedGroup(detail);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add member');
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedGroup) return;
    try {
      await groupService.removeMember(selectedGroup.id, userId);
      setSuccess('Member removed');
      const detail = await groupService.get(selectedGroup.id);
      setSelectedGroup(detail);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove member');
    }
  };

  // Check is admin
  const userInfo = authService.getUserInfo();
  const isAdmin = userInfo?.is_superuser || userInfo?.role === 'admin';

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">Groups</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => {
          setFormData({ name: '', description: '' });
          setCreateDialogOpen(true);
        }}>
          Create Group
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      {loading ? (
        <Typography>Loading...</Typography>
      ) : groups.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">No groups yet. Create your first group to get started.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Members</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {groups.map((group) => (
                <TableRow key={group.id} hover>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <GroupIcon color="primary" />
                      <Typography fontWeight="medium">{group.name}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{group.description || '-'}</TableCell>
                  <TableCell>
                    <Chip label={`${group.member_count} member${group.member_count !== 1 ? 's' : ''}`} size="small" />
                  </TableCell>
                  <TableCell>{new Date(group.created_at).toLocaleDateString()}</TableCell>
                  <TableCell align="right">
                    <IconButton onClick={() => openMemberDialog(group)} title="Manage Members" color="primary">
                      <PersonAddIcon />
                    </IconButton>
                    <IconButton onClick={() => openEditDialog(group)} title="Edit Group" color="primary">
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => { setSelectedGroup(group as any); setDeleteDialogOpen(true); }} title="Delete Group" color="error">
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Group</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus margin="dense" label="Group Name" fullWidth required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
          <TextField
            margin="dense" label="Description" fullWidth multiline rows={3}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained" disabled={!formData.name.trim()}>Create</Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Group</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus margin="dense" label="Group Name" fullWidth required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
          <TextField
            margin="dense" label="Description" fullWidth multiline rows={3}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleEdit} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Group</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{selectedGroup?.name}"? This will also remove all member associations.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">Delete</Button>
        </DialogActions>
      </Dialog>

      {/* Members Dialog */}
      <Dialog open={memberDialogOpen} onClose={() => setMemberDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <span>Members: {selectedGroup?.name}</span>
            <Button startIcon={<PersonAddIcon />} onClick={openAddMemberDialog} size="small" variant="outlined">
              Add
            </Button>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedGroup?.members && selectedGroup.members.length > 0 ? (
            <List>
              {selectedGroup.members.map((member) => (
                <React.Fragment key={member.user_id}>
                  <ListItem
                    secondaryAction={
                      <IconButton edge="end" onClick={() => handleRemoveMember(member.user_id)} color="error" size="small">
                        <PersonRemoveIcon />
                      </IconButton>
                    }
                  >
                    <ListItemAvatar>
                      <Avatar>{member.username[0]?.toUpperCase()}</Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={member.username}
                      secondary={`${member.email} · ${member.role}`}
                    />
                  </ListItem>
                  <Divider />
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Typography color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
              No members yet
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMemberDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Add Member Dialog */}
      <Dialog open={addMemberDialogOpen} onClose={() => setAddMemberDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Member</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense">
            <InputLabel>User</InputLabel>
            <Select
              value={addMemberForm.user_id}
              label="User"
              onChange={(e) => setAddMemberForm({ ...addMemberForm, user_id: e.target.value })}
            >
              {users.map((u) => (
                <MenuItem key={u.id} value={u.id}>{u.username} ({u.email})</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense">
            <InputLabel>Role</InputLabel>
            <Select
              value={addMemberForm.role}
              label="Role"
              onChange={(e) => setAddMemberForm({ ...addMemberForm, role: e.target.value })}
            >
              <MenuItem value="member">Member</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddMemberDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAddMember} variant="contained" disabled={!addMemberForm.user_id}>Add</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdminGroups;
