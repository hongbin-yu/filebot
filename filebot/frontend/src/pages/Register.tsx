import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import authService from '../services/auth.service';

const Register: React.FC = () => {
  const [formData, setFormData] = useState({ username: '', email: '', password: '', confirmPassword: '', fullName: '' });
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const validateForm = (): boolean => {
    const newErrors: string[] = [];
    if (!formData.username.trim()) newErrors.push('Username is required');
    else if (formData.username.length < 3) newErrors.push('Username must be at least 3 characters');
    if (!formData.email.trim()) newErrors.push('Email is required');
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) newErrors.push('Please enter a valid email address');
    if (!formData.password) newErrors.push('Password is required');
    else if (formData.password.length < 6) newErrors.push('Password must be at least 6 characters');
    if (formData.password !== formData.confirmPassword) newErrors.push('Passwords do not match');
    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    setLoading(true); setErrors([]);
    try {
      const success = await authService.register({ username: formData.username, email: formData.email, password: formData.password, full_name: formData.fullName });
      if (success) {
        const loginSuccess = await authService.login(formData.email, formData.password);
        navigate(loginSuccess ? '/' : '/login');
      } else { setErrors(['Registration failed. The username or email may already be taken.']); }
    } catch (error: any) { setErrors([error.message || 'Registration failed. Please try again.']); }
    finally { setLoading(false); }
  };

  return (
    <div className="fb-page-bg">
      <div className="container">
        <div className="row">
          <div className="col-md-6 col-md-offset-3" style={{ paddingTop: 40 }}>
            <div className="text-center" style={{ marginBottom: 25 }}>
              <p style={{ fontSize: '3em', margin: 0 }}>🚀</p>
              <h2>Create your FileBot account</h2>
              <p className="text-muted">
                Already have an account? <Link to="/login" className="text-primary">Sign in here</Link>
              </p>
            </div>

            <div className="panel panel-default">
              <div className="panel-body" style={{ padding: 30 }}>
                <form onSubmit={handleSubmit}>
                  <div className="form-group">
                    <label htmlFor="fullName">Full Name (Optional)</label>
                    <input id="fullName" name="fullName" type="text" autoComplete="name"
                      className="form-control" placeholder="John Doe" value={formData.fullName}
                      onChange={handleChange} disabled={loading} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="username">Username *</label>
                    <input id="username" name="username" type="text" autoComplete="username" required
                      className="form-control" placeholder="johndoe" value={formData.username}
                      onChange={handleChange} disabled={loading} />
                    <small className="text-muted">3-30 characters, letters, numbers, and underscores only</small>
                  </div>
                  <div className="form-group">
                    <label htmlFor="email">Email address *</label>
                    <input id="email" name="email" type="email" autoComplete="email" required
                      className="form-control" placeholder="you@example.com" value={formData.email}
                      onChange={handleChange} disabled={loading} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="password">Password *</label>
                    <input id="password" name="password" type="password" autoComplete="new-password" required
                      className="form-control" placeholder="••••••••" value={formData.password}
                      onChange={handleChange} disabled={loading} />
                    <small className="text-muted">At least 6 characters, with letters and numbers</small>
                  </div>
                  <div className="form-group">
                    <label htmlFor="confirmPassword">Confirm Password *</label>
                    <input id="confirmPassword" name="confirmPassword" type="password" autoComplete="new-password" required
                      className="form-control" placeholder="••••••••" value={formData.confirmPassword}
                      onChange={handleChange} disabled={loading} />
                  </div>
                  <div className="checkbox">
                    <label><input type="checkbox" required disabled={loading} /> I agree to the Terms of Service and Privacy Policy</label>
                  </div>

                  {errors.length > 0 && (
                    <div className="alert alert-danger">
                      <strong>{errors.length === 1 ? 'Error' : 'Errors'} occurred</strong>
                      <ul style={{ marginBottom: 0, paddingLeft: 20, marginTop: 5 }}>
                        {errors.map((error, idx) => <li key={idx}>{error}</li>)}
                      </ul>
                    </div>
                  )}

                  <button type="submit" className={'btn btn-primary btn-block' + (loading ? ' disabled' : '')}
                    disabled={loading} style={{ marginTop: 15 }}>
                    {loading ? 'Creating account...' : 'Create Account'}
                  </button>
                </form>

                <hr />
                <h4 className="text-muted">Why join FileBot?</h4>
                <ul className="list-unstyled" style={{ lineHeight: 2 }}>
                  <li><span className="glyphicon glyphicon-ok text-success"></span> Unlimited document storage</li>
                  <li><span className="glyphicon glyphicon-ok text-success"></span> Advanced search and organization</li>
                  <li><span className="glyphicon glyphicon-ok text-success"></span> Collaborate with team members</li>
                  <li><span className="glyphicon glyphicon-ok text-success"></span> Secure and private by design</li>
                  <li><span className="glyphicon glyphicon-ok text-success"></span> Free for personal use</li>
                </ul>

                <div className="text-center" style={{ marginTop: 15 }}>
                  <p className="text-muted" style={{ fontSize: '0.85em' }}>
                    Already have an account? <Link to="/login" className="text-primary">Sign in instead</Link>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
