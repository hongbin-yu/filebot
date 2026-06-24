import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Chip, Alert, Snackbar,
  FormControl, InputLabel, Select, MenuItem, TextField, Tabs, Tab,
  Card, CardContent, Grid
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Security as SecurityIcon } from '@mui/icons-material';
import permissionService, { Permission, PermissionCreate } from '../../services/permission.service';
import groupService, { Group } from '../../services/group.service';
import authService from '../../services/auth.service';
import institutionService from '../../services/institution.service';

interface App {
  id: string;
  name: string;
  slug: string;
}

const AdminPermissions: React.FC = () => {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [apps, setApps] = useState<App[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [users, setUsers] = useState<{ id: string; username: string; email: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [tabValue, setTabValue] = useState(0);

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [assignType, setAssignType] = useState<'user' | 'group'>('user');
  interface FolderOption {
    path: string;
    name: string;
  }

  const [formData, setFormData] = useState({
    resource_type: 'app' as 'app' | 'folder',
    resource_id: '',
    assignee_id: '',
    permission_level: 'read' as 'read' | 'write' | 'admin' | 'owner',
    folder_app_id: '',
  });
  const [folderLevels, setFolderLevels] = useState<FolderOption[][]>([]);
  const [folderSelections, setFolderSelections] = useState<string[]>([]);
  const [loadingLevel, setLoadingLevel] = useState(false);

  // Institution filter
  const [institutions, setInstitutions] = useState<{ id: string; name: string }[]>([]);
  const [institutionFilter, setInstitutionFilter] = useState('');

  const loadPermissions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await permissionService.list();
      setPermissions(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load permissions');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadApps = useCallback(async () => {
    try {
      const response = await (await import('../../services/api')).default.get('/apps/');
      setApps(response.data);
    } catch { /* ignore */ }
  }, []);

  const loadGroups = useCallback(async () => {
    try {
      const data = await groupService.list();
      setGroups(data);
    } catch { /* ignore */ }
  }, []);

  const loadUsers = useCallback(async () => {
    try {
      const response = await (await import('../../services/api')).default.get('/users/');
      setUsers(response.data);
    } catch { /* ignore */ }
  }, []);

  const loadInstitutions = useCallback(async () => {
    try {
      const data = await institutionService.getInstitutions();
      setInstitutions(data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadPermissions();
    loadApps();
    loadGroups();
    loadUsers();
    loadInstitutions();
  }, [loadPermissions, loadApps, loadGroups, loadUsers, loadInstitutions]);

  const handleCreate = async () => {
    if (!formData.resource_id || !formData.assignee_id) return;
    try {
      const payload: PermissionCreate = {
        resource_type: formData.resource_type,
        resource_id: formData.resource_id,
        permission_level: formData.permission_level,
      };
      if (assignType === 'user') {
        payload.user_id = formData.assignee_id;
      } else {
        payload.group_id = formData.assignee_id;
      }
      await permissionService.create(payload);
      setSuccess('Permission assigned');
      setDialogOpen(false);
      setFormData({ resource_type: 'app', resource_id: '', assignee_id: '', permission_level: 'read', folder_app_id: '' });
      setFolderLevels([]);
      setFolderSelections([]);
      loadPermissions();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to assign permission');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await permissionService.delete(id);
      setSuccess('Permission removed');
      loadPermissions();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove permission');
    }
  };

  // Load direct children of a given parent folder path
  const loadFolderLevel = async (appId: string, parentPath: string): Promise<FolderOption[]> => {
    try {
      const res = await (await import('../../services/api')).default.get(
        `/folders/?app_id=${appId}&parent_folder_path=${encodeURIComponent(parentPath)}`
      );
      return res.data.map((f: any) => ({
        path: f.path,
        name: f.name || f.title || f.path.split('/').pop(),
      }));
    } catch {
      return [];
    }
  };

  // When app is selected for folder browsing — load first level
  const handleFolderAppChange = async (appId: string) => {
    const app = apps.find(a => a.id === appId);
    setFormData({ ...formData, folder_app_id: appId, resource_id: '' });
    setFolderLevels([]);
    setFolderSelections([]);
    if (!app) return;
    setLoadingLevel(true);
    const rootLevel = await loadFolderLevel(appId, '/' + app.slug);
    if (rootLevel.length > 0) setFolderLevels([rootLevel]);
    setLoadingLevel(false);
  };

  const getResourceName = (perm: Permission): string => {
    if (perm.resource_type === 'app') {
      if (perm.resource_id === '*') return 'All Apps';
      const app = apps.find(a => a.id === perm.resource_id);
      return app ? app.name : perm.resource_id;
    }
    return perm.resource_id;
  };

  const getAssigneeName = (perm: Permission): string => {
    if (perm.user_id) {
      const user = users.find(u => u.id === perm.user_id);
      return user ? user.username : perm.user_id;
    }
    if (perm.group_id) {
      const group = groups.find(g => g.id === perm.group_id);
      return group ? group.name : perm.group_id;
    }
    return 'Unknown';
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'owner': return 'error';
      case 'admin': return 'warning';
      case 'write': return 'info';
      case 'read': return 'success';
      default: return 'default';
    }
  };

  // Current user info for superuser check
  const [currentUser, setCurrentUser] = useState<any>(null);
  useEffect(() => {
    authService.getCurrentUser().then(u => setCurrentUser(u)).catch(() => {});
  }, []);

  const isSuperuser = currentUser?.is_superuser === true;

  // Filter by tab + institution
  let filteredPermissions = tabValue === 0
    ? permissions.filter(p => p.resource_type === 'app')
    : permissions.filter(p => p.resource_type === 'folder');

  if (institutionFilter) {
    filteredPermissions = filteredPermissions.filter(p => p.institution_id === institutionFilter);
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">Permissions</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => {
          setDialogOpen(true);
        }}>
          Assign Permission
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 2 }}>
        <Tab label="App Permissions" />
        <Tab label="Folder Permissions" />
      </Tabs>

      {isSuperuser && (
        <FormControl sx={{ mb: 2, minWidth: 280 }} size="small">
          <InputLabel>Filter by Institution</InputLabel>
          <Select
            value={institutionFilter}
            label="Filter by Institution"
            onChange={(e) => setInstitutionFilter(e.target.value)}
          >
            <MenuItem value="">All Institutions</MenuItem>
            {institutions.map(inst => (
              <MenuItem key={inst.id} value={inst.id}>{inst.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {loading ? (
        <Typography>Loading...</Typography>
      ) : filteredPermissions.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <SecurityIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography color="text.secondary">
            No {tabValue === 0 ? 'app' : 'folder'} permissions yet.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Resource</TableCell>
                <TableCell>Assignee</TableCell>
                <TableCell>Institution</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Level</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredPermissions.map((perm) => (
                <TableRow key={perm.id} hover>
                  <TableCell>
                    <Typography fontWeight="medium">{getResourceName(perm)}</Typography>
                    <Typography variant="caption" color="text.secondary">{perm.resource_id}</Typography>
                  </TableCell>
                  <TableCell>{getAssigneeName(perm)}</TableCell>
                  <TableCell>
                    <Chip
                      label={perm.institution_name || '-'}
                      size="small"
                      variant="outlined"
                      sx={{ maxWidth: 180 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={perm.user_id ? 'User' : 'Group'}
                      size="small"
                      color={perm.user_id ? 'primary' : 'secondary'}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip label={perm.permission_level} size="small" color={getLevelColor(perm.permission_level) as any} />
                  </TableCell>
                  <TableCell>{new Date(perm.created_at).toLocaleDateString()}</TableCell>
                  <TableCell align="right">
                    <IconButton onClick={() => handleDelete(perm.id)} color="error" title="Remove Permission">
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Assign Permission Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Assign Permission</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense">
            <InputLabel>Assign To</InputLabel>
            <Select value={assignType} label="Assign To" onChange={(e) => setAssignType(e.target.value as 'user' | 'group')}>
              <MenuItem value="user">User</MenuItem>
              <MenuItem value="group">Group</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth margin="dense">
            <InputLabel>{assignType === 'user' ? 'User' : 'Group'}</InputLabel>
            <Select
              value={formData.assignee_id}
              label={assignType === 'user' ? 'User' : 'Group'}
              onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value })}
            >
              {assignType === 'user'
                ? users.map(u => <MenuItem key={u.id} value={u.id}>{u.username} ({u.email})</MenuItem>)
                : groups.map(g => <MenuItem key={g.id} value={g.id}>{g.name} ({g.member_count} members)</MenuItem>)
              }
            </Select>
          </FormControl>

          <FormControl fullWidth margin="dense">
            <InputLabel>Resource Type</InputLabel>
            <Select
              value={formData.resource_type}
              label="Resource Type"
              onChange={(e) => { setFormData({ ...formData, resource_type: e.target.value as 'app' | 'folder', resource_id: '' }); }}
            >
              <MenuItem value="app">App</MenuItem>
              <MenuItem value="folder">Folder</MenuItem>
            </Select>
          </FormControl>

          {formData.resource_type === 'folder' && (
            <FormControl fullWidth margin="dense">
              <InputLabel>App</InputLabel>
              <Select
                value={formData.folder_app_id}
                label="App"
                onChange={(e) => handleFolderAppChange(e.target.value)}
              >
                <MenuItem value="" disabled>Select an app...</MenuItem>
                {apps.map(a => <MenuItem key={a.id} value={a.id}>{a.name} ({a.slug})</MenuItem>)}
              </Select>
            </FormControl>
          )}
          {formData.resource_type === 'folder' && formData.folder_app_id && (
            <Box sx={{ ml: 1, mt: 1, mb: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                Browse folders level by level:
              </Typography>
              {folderLevels.map((level, idx) => (
                <FormControl key={idx} fullWidth margin="dense">
                  <InputLabel>Level {idx + 1}</InputLabel>
                  <Select
                    value={folderSelections[idx] || ''}
                    label={`Level ${idx + 1}`}
                    onChange={async (e) => {
                      const path = e.target.value;
                      const newSelections = [...folderSelections.slice(0, idx), path];
                      setFolderSelections(newSelections);
                      setFormData({ ...formData, resource_id: path });
                      setLoadingLevel(true);
                      const children = await loadFolderLevel(formData.folder_app_id, path);
                      if (children.length > 0) {
                        setFolderLevels(prev => [...prev.slice(0, idx + 1), children]);
                      } else {
                        setFolderLevels(prev => prev.slice(0, idx + 1));
                      }
                      setLoadingLevel(false);
                    }}
                  >
                    <MenuItem value="" disabled>Select...</MenuItem>
                    {level.map(f => (
                      <MenuItem key={f.path} value={f.path}>{f.name}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ))}
              {loadingLevel && <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>Loading...</Typography>}
              {folderSelections.length > 0 && !loadingLevel && (
                <TextField
                  fullWidth
                  margin="dense"
                  label="Resource Path"
                  value={folderSelections[folderSelections.length - 1]}
                  InputProps={{ readOnly: true }}
                  size="small"
                  sx={{ mt: 1 }}
                />
              )}
            </Box>
          )}
          {formData.resource_type === 'app' && (
            <FormControl fullWidth margin="dense">
              <InputLabel>Resource</InputLabel>
              <Select
                value={formData.resource_id}
                label="Resource"
                onChange={(e) => setFormData({ ...formData, resource_id: e.target.value })}
              >
                {[<MenuItem key="*" value="*">All Apps</MenuItem>, ...apps.map(a => <MenuItem key={a.id} value={a.id}>{a.name} ({a.slug})</MenuItem>)]}
              </Select>
            </FormControl>
          )}

          <FormControl fullWidth margin="dense">
            <InputLabel>Permission Level</InputLabel>
            <Select
              value={formData.permission_level}
              label="Permission Level"
              onChange={(e) => setFormData({ ...formData, permission_level: e.target.value as any })}
            >
              <MenuItem value="read">Read</MenuItem>
              <MenuItem value="write">Write</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
              <MenuItem value="owner">Owner</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained" disabled={!formData.resource_id || !formData.assignee_id}>
            Assign
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdminPermissions;
