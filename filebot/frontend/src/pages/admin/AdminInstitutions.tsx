import React, { useState, useEffect } from 'react';
import institutionService, { Institution, InstitutionUpdate } from '../../services/institution.service';
import { showToast } from '../../components/common/ToastNotification';

const AdminInstitutions: React.FC = () => {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDomain, setNewDomain] = useState('');
  const [creating, setCreating] = useState(false);

  // Edit modal
  const [editing, setEditing] = useState<Institution | null>(null);
  const [editName, setEditName] = useState('');
  const [editSlug, setEditSlug] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editDomain, setEditDomain] = useState('');
  const [editIsActive, setEditIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadInst = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await institutionService.getAllInstitutions();
      setInstitutions(data);
    } catch (err) {
      console.error('Failed to load institutions:', err);
      setError('Failed to load institutions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadInst(); }, []);

  const handleCreate = async () => {
    if (!newName.trim() || !newSlug.trim()) {
      showToast('Name and slug are required', 'error');
      return;
    }
    try {
      setCreating(true);
      await institutionService.createInstitution({
        name: newName.trim(),
        slug: newSlug.trim().toLowerCase().replace(/\s+/g, '-'),
        description: newDesc.trim() || undefined,
        domain: newDomain.trim() || undefined,
      });
      setShowCreateForm(false);
      setNewName('');
      setNewSlug('');
      setNewDesc('');
      setNewDomain('');
      showToast('Institution created', 'success');
      loadInst();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Creation failed';
      showToast(detail, 'error');
    } finally {
      setCreating(false);
    }
  };

  const openEdit = (inst: Institution) => {
    setEditing(inst);
    setEditName(inst.name);
    setEditSlug(inst.slug);
    setEditDesc(inst.description || '');
    setEditDomain(inst.domain || '');
    setEditIsActive(inst.is_active);
  };

  const handleSave = async () => {
    if (!editing) return;
    try {
      setSaving(true);
      const data: InstitutionUpdate = {};
      if (editName !== editing.name) data.name = editName;
      if (editSlug !== editing.slug) data.slug = editSlug;
      if (editDesc !== (editing.description || '')) data.description = editDesc || undefined;
      if (editDomain !== (editing.domain || '')) data.domain = editDomain || undefined;
      if (editIsActive !== editing.is_active) data.is_active = editIsActive;

      await institutionService.updateInstitution(editing.id, data);
      setEditing(null);
      showToast('Institution updated', 'success');
      loadInst();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Update failed';
      showToast(detail, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (inst: Institution) => {
    const confirmed = await window.wetYesOrNo(
      `Delete institution "${inst.name}"? Users assigned to it must be reassigned first.`
    );
    if (!confirmed) return;
    try {
      await institutionService.deleteInstitution(inst.id);
      showToast(`Institution "${inst.name}" deleted`, 'success');
      loadInst();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Delete failed';
      showToast(detail, 'error');
    }
  };

  if (loading) {
    return (
      <div style={{padding:24}}>
        <h1 style={{fontSize:"1.125rem",fontSize:"1.5rem",fontWeight:700,color:"#1f2937",display:"none",display:"block",marginBottom:24}}>Institution Management</h1>
        <div className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}>
          <div >
            <div className="fb-spinner" style={{display:"inline-block",borderRadius:4,height:48,width:48,borderBottomWidth:8,borderColor:"#2563eb"}}></div>
            <p style={{marginTop:16,color:"#4b5563"}}>Loading institutions...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{padding:24}}>
        <h1 style={{fontSize:"1.125rem",fontSize:"1.5rem",fontWeight:700,color:"#1f2937",display:"none",display:"block",marginBottom:24}}>Institution Management</h1>
        <div  style={{background:"#fef2f2",border:"1px solid",borderColor:"#fecaca",borderRadius:4,padding:24}}>
          <p style={{color:"#b91c1c",marginBottom:16}}>{error}</p>
          <button onClick={loadInst} className="fb-hover-btn" style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,background:"#dc2626",color:"#ffffff",borderRadius:4}}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{padding:24}}>
      <div className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16,marginBottom:24}}>
        <h1 style={{fontSize:"1.125rem",fontSize:"1.5rem",fontWeight:700,color:"#1f2937",display:"none",display:"block"}}>Institution Management</h1>
        <div className="fb-d-flex fb-align-center" style={{gap:8}}>
          <span style={{fontSize:"0.875rem",color:"#6b7280"}}>{institutions.length} institution{institutions.length !== 1 ? 's' : ''}</span>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="fb-hover-btn" style={{paddingLeft:12,paddingRight:12,paddingTop:6,paddingBottom:6,background:"#2563eb",color:"#ffffff",fontSize:"0.875rem",borderRadius:4}}
          >
            {showCreateForm ? 'Cancel' : '+ New'}
          </button>
        </div>
      </div>

      {/* Create form */}
      {showCreateForm && (
        <div style={{background:"#eff6ff",border:"1px solid",borderColor:"#bfdbfe",borderRadius:4,padding:16,marginBottom:24}}>
          <h3 style={{fontSize:"0.875rem",fontWeight:600,color:"#1e40af",marginBottom:12}}>Create New Institution</h3>
          <div style={{display:"grid",gridTemplateColumns:"repeat(1, minmax(0, 1fr))",gridTemplateColumns:"repeat(2, minmax(0, 1fr))",gap:12}}>
            <div>
              <label style={{display:"block",fontSize:"0.75rem",fontWeight:500,color:"#1d4ed8",marginBottom:4}}>Name *</label>
              <input
                type="text" value={newName} onChange={e => setNewName(e.target.value)}
                style={{width:"100%",border:"1px solid",borderColor:"#93c5fd",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}}
                placeholder="e.g. Employment and Social Development Canada"
              />
            </div>
            <div>
              <label style={{display:"block",fontSize:"0.75rem",fontWeight:500,color:"#1d4ed8",marginBottom:4}}>Slug *</label>
              <input
                type="text" value={newSlug} onChange={e => setNewSlug(e.target.value)}
                style={{width:"100%",border:"1px solid",borderColor:"#93c5fd",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}}
                placeholder="e.g. esdc"
              />
            </div>
            <div>
              <label style={{display:"block",fontSize:"0.75rem",fontWeight:500,color:"#1d4ed8",marginBottom:4}}>Description</label>
              <input
                type="text" value={newDesc} onChange={e => setNewDesc(e.target.value)}
                style={{width:"100%",border:"1px solid",borderColor:"#93c5fd",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}}
                placeholder="Optional description"
              />
            </div>
            <div>
              <label style={{display:"block",fontSize:"0.75rem",fontWeight:500,color:"#1d4ed8",marginBottom:4}}>Domain</label>
              <input
                type="text" value={newDomain} onChange={e => setNewDomain(e.target.value)}
                style={{width:"100%",border:"1px solid",borderColor:"#93c5fd",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}}
                placeholder="e.g. canada.ca"
              />
            </div>
          </div>
          <div className="fb-d-flex fb-justify-end" style={{marginTop:12}}>
            <button
              onClick={handleCreate} disabled={creating}
              className="fb-hover-btn" style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,background:"#2563eb",color:"#ffffff",fontSize:"0.875rem",borderRadius:4}}
            >
              {creating ? 'Creating...' : 'Create Institution'}
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {institutions.length === 0 ? (
        <div  style={{background:"#fefce8",border:"1px solid",borderColor:"#fef08a",borderRadius:4,padding:32}}>
          <p style={{color:"#a16207"}}>No institutions yet.</p>
        </div>
      ) : (
        <div style={{background:"#ffffff",borderRadius:4,boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)",overflow:"hidden"}}>
          <div style={{overflowX:"auto"}}>
            <table className="fb-divide-y" style={{ minWidth:"100%" }}>
              <thead style={{background:"#f9fafb"}}>
                <tr>
                  <th  style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",fontWeight:500,color:"#6b7280",textTransform:"uppercase",letterSpacing:"0.05em"}}>Name</th>
                  <th  style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",fontWeight:500,color:"#6b7280",textTransform:"uppercase",letterSpacing:"0.05em"}}>Slug</th>
                  <th  style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",fontWeight:500,color:"#6b7280",textTransform:"uppercase",letterSpacing:"0.05em"}}>Domain</th>
                  <th  style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",fontWeight:500,color:"#6b7280",textTransform:"uppercase",letterSpacing:"0.05em"}}>Status</th>
                  <th  style={{paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,fontSize:"0.75rem",fontWeight:500,color:"#6b7280",textTransform:"uppercase",letterSpacing:"0.05em"}}>Actions</th>
                </tr>
              </thead>
              <tbody className="fb-divide-y"  style={{ "--divide-color":"#e5e7eb", background:"#ffffff" }}>
                {institutions.map(inst => (
                  <tr key={inst.id} className="fb-hover-btn">
                    <td style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",fontWeight:500,color:"#111827"}}>{inst.name}</td>
                    <td style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",color:"#6b7280",fontFamily:"monospace"}}>{inst.slug}</td>
                    <td style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",color:"#6b7280"}}>{inst.domain || '—'}</td>
                    <td style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap"}}>
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        inst.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {inst.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td  style={{paddingLeft:24,paddingRight:24,paddingTop:16,paddingBottom:16,whiteSpace:"nowrap",fontSize:"0.875rem",fontWeight:500}}>
                      <div className="fb-d-flex fb-justify-end" style={{columnGap:8}}>
                        <button
                          onClick={() => openEdit(inst)}
                          className="fb-hover-btn" style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,background:"#dbeafe",color:"#1e40af",borderRadius:4,fontSize:"0.75rem"}}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(inst)}
                          className="fb-hover-btn" style={{paddingLeft:12,paddingRight:12,paddingTop:4,paddingBottom:4,background:"#fee2e2",color:"#991b1b",borderRadius:4,fontSize:"0.75rem"}}
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

      {/* Edit modal */}
      {editing && (
        <div style={{position:"fixed",top:0,right:0,bottom:0,left:0,zIndex:500,overflowY:"auto"}}>
          <div className="fb-d-flex fb-align-center fb-justify-center" style={{minHeight:"100vh",paddingLeft:16,paddingRight:16}}>
            <div style={{position:"fixed",top:0,right:0,bottom:0,left:0,background:"#6b7280",opacity:0.75,transition:"opacity 0.2s ease"}} onClick={() => setEditing(null)}></div>
            <div style={{position:"relative",background:"#ffffff",borderRadius:4,boxShadow:"0 20px 25px -5px rgba(0,0,0,0.1)",maxWidth:448,width:"100%",padding:24,zIndex:100}}>
              <h3 style={{fontSize:"1.125rem",fontWeight:600,marginBottom:16}}>Edit Institution</h3>
              <div style={{rowGap:12}}>
                <div>
                  <label style={{display:"block",fontSize:"0.875rem",fontWeight:500,color:"#374151",marginBottom:4}}>Name</label>
                  <input type="text" value={editName} onChange={e => setEditName(e.target.value)}
                    style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}} />
                </div>
                <div>
                  <label style={{display:"block",fontSize:"0.875rem",fontWeight:500,color:"#374151",marginBottom:4}}>Slug</label>
                  <input type="text" value={editSlug} onChange={e => setEditSlug(e.target.value)}
                    style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}} />
                </div>
                <div>
                  <label style={{display:"block",fontSize:"0.875rem",fontWeight:500,color:"#374151",marginBottom:4}}>Description</label>
                  <input type="text" value={editDesc} onChange={e => setEditDesc(e.target.value)}
                    style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}} />
                </div>
                <div>
                  <label style={{display:"block",fontSize:"0.875rem",fontWeight:500,color:"#374151",marginBottom:4}}>Domain</label>
                  <input type="text" value={editDomain} onChange={e => setEditDomain(e.target.value)}
                    style={{width:"100%",border:"1px solid",borderColor:"#d1d5db",borderRadius:4,paddingLeft:12,paddingRight:12,paddingTop:8,paddingBottom:8,fontSize:"0.875rem",outline:"none",boxShadow:"0 0 0 8px rgba(59,130,246,0.5)",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}} />
                </div>
                <div className="fb-d-flex fb-align-center">
                  <input type="checkbox" id="edit-active" checked={editIsActive}
                    onChange={e => setEditIsActive(e.target.checked)}
                    style={{height:16,width:16,color:"#2563eb",boxShadow:"0 0 0 2px rgba(59,130,246,0.5)",borderColor:"#d1d5db",borderRadius:4}} />
                  <label htmlFor="edit-active" style={{marginLeft:8,fontSize:"0.875rem",color:"#374151"}}>Active</label>
                </div>
              </div>
              <div className="fb-d-flex fb-justify-end" style={{marginTop:24,columnGap:12}}>
                <button onClick={() => setEditing(null)}
                  className="fb-hover-btn" style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,background:"#f3f4f6",color:"#374151",borderRadius:4,fontSize:"0.875rem"}}>Cancel</button>
                <button onClick={handleSave} disabled={saving}
                  className="fb-hover-btn" style={{paddingLeft:16,paddingRight:16,paddingTop:8,paddingBottom:8,background:"#2563eb",color:"#ffffff",borderRadius:4,fontSize:"0.875rem"}}>
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

export default AdminInstitutions;
