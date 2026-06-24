import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import authService from '../services/auth.service';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectUrl = searchParams.get('redirect');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors([]);
    setLoading(true);
    try {
      const success = await authService.login(username, password);
      if (success) {
        if (redirectUrl && redirectUrl.startsWith('http')) {
          const token = localStorage.getItem('access_token');
          const user = localStorage.getItem('user_info');
          const separator = redirectUrl.includes('?') ? '&' : '?';
          window.location.href = redirectUrl + separator + 'token=' + encodeURIComponent(token || '') + '&user=' + encodeURIComponent(user || '');
        } else { navigate('/'); }
      } else { setErrors(['Invalid username or password']); }
    } catch (error: any) { setErrors([error.message || 'Login failed. Please try again.']); }
    finally { setLoading(false); }
  };

  return (
    <div className="fb-page-bg">
      <div className="container">
        <div className="row">
          <div className="col-md-6 col-md-offset-3" style={{ paddingTop: 60 }}>
            <div className="text-center" style={{ marginBottom: 30 }}>
              <p style={{ fontSize: '3em', margin: 0 }}>🔐</p>
              <h2>Sign in to WebFileBot</h2>
              <p className="text-muted">Enter your credentials to access your documents</p>
            </div>

            <div className="panel panel-default">
              <div className="panel-body" style={{ padding: 30 }}>
                <form onSubmit={handleSubmit}>
                  <div className="form-group">
                    <label htmlFor="username">Username or Email</label>
                    <input id="username" name="username" type="text" autoComplete="username"
                      required className="form-control" placeholder="demo or demo@filebot.app"
                      value={username} onChange={e => setUsername(e.target.value)} disabled={loading} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input id="password" name="password" type="password" autoComplete="current-password"
                      required className="form-control" placeholder="••••••••"
                      value={password} onChange={e => setPassword(e.target.value)} disabled={loading} />
                  </div>
                  <div className="checkbox">
                    <label>
                      <input type="checkbox" checked={rememberMe}
                        onChange={e => setRememberMe(e.target.checked)} disabled={loading} />
                      Remember me
                    </label>
                    <a href="#" className="text-primary pull-right text-muted" style={{ fontSize: '0.85em' }}>Forgot your password?</a>
                  </div>

                  {errors.length > 0 && (
                    <div className="alert alert-danger">
                      <strong>{errors.length === 1 ? 'Error' : 'Errors'} occurred</strong>
                      <ul style={{ marginBottom: 0, paddingLeft: 20, marginTop: 5 }}>
                        {errors.map((error, idx) => <li key={idx}>{error}</li>)}
                      </ul>
                    </div>
                  )}

                  <button type="submit" className={'btn btn-primary btn-block' + (loading ? ' disabled' : '')} disabled={loading}
                    style={{ marginTop: 15 }}>
                    {loading ? 'Signing in...' : 'Sign in'}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
