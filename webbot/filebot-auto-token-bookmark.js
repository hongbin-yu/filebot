// Bookmarklet for auto-filling FileBot API Docs with token
// Save this as a bookmark with the following code (minified version below):

javascript:(function() {
    // Get token from WebBot backend
    fetch('http://localhost:8000/api/v1/auth/filebot-token')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const token = data.access_token;
            
            // Check if we're on FileBot API docs page
            if (window.location.href.includes('localhost:8001/api/docs')) {
                // Try to find and fill Swagger UI authorize form
                autoFillSwaggerUI(token);
            } else {
                // If not on docs page, ask to navigate
                const goToDocs = confirm(
                    'Token fetched successfully!\n' +
                    `Token: ${token.substring(0, 30)}...\n\n` +
                    'Do you want to open FileBot API Docs?'
                );
                if (goToDocs) {
                    window.open('http://localhost:8001/api/docs', '_blank');
                } else {
                    // Show token for manual copy
                    showTokenPopup(token);
                }
            }
        })
        .catch(error => {
            alert(`Error fetching token: ${error.message}\n\nMake sure WebBot is running on port 8000.`);
        });
    
    function autoFillSwaggerUI(token) {
        // Try multiple approaches to fill Swagger UI
        let filled = false;
        
        // Approach 1: Try to click the authorize button and fill the modal
        const authorizeButtons = document.querySelectorAll('.btn.authorize');
        if (authorizeButtons.length > 0) {
            authorizeButtons[0].click();
            
            // Wait for modal to appear
            setTimeout(() => {
                const authInputs = document.querySelectorAll('input[type="text"][placeholder*="Bearer"], input[type="text"][placeholder*="Token"]');
                if (authInputs.length > 0) {
                    authInputs[0].value = `Bearer ${token}`;
                    filled = true;
                    
                    // Try to click the authorize button in the modal
                    setTimeout(() => {
                        const modalAuthorizeBtn = document.querySelector('.auth-btn-wrapper .btn.authorize, .modal-footer .btn.authorize');
                        if (modalAuthorizeBtn) {
                            modalAuthorizeBtn.click();
                        }
                    }, 100);
                }
            }, 300);
        }
        
        // Approach 2: Try to set token directly in localStorage (if Swagger UI stores it there)
        try {
            const swaggerConfig = JSON.parse(localStorage.getItem('swagger-ui') || '{}');
            if (swaggerConfig.authorized && swaggerConfig.authorized.Bearer) {
                swaggerConfig.authorized.Bearer.value = `Bearer ${token}`;
                localStorage.setItem('swagger-ui', JSON.stringify(swaggerConfig));
                filled = true;
            }
        } catch (e) {
            console.log('Could not access localStorage:', e);
        }
        
        // Approach 3: Try to trigger swagger-ui authorize event
        if (window.ui && window.ui.authActions) {
            try {
                window.ui.authActions.authorize({
                    Bearer: {
                        name: 'Bearer',
                        value: `Bearer ${token}`
                    }
                });
                filled = true;
            } catch (e) {
                console.log('Swagger UI authActions not available:', e);
            }
        }
        
        if (filled) {
            alert('✅ Token auto-filled successfully!\n\nYou can now use the FileBot API docs with the token.');
        } else {
            showTokenPopup(token, 'FileBot API Docs detected but could not auto-fill. Please paste this token manually:');
        }
    }
    
    function showTokenPopup(token, message = 'Token fetched successfully:') {
        const popup = document.createElement('div');
        popup.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.3);
            z-index: 999999;
            max-width: 90%;
            width: 500px;
            font-family: Arial, sans-serif;
        `;
        
        popup.innerHTML = `
            <h3 style="margin-top: 0; color: #4CAF50;">🔐 FileBot Token</h3>
            <p>${message}</p>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; word-break: break-all; font-family: monospace;">
                Bearer ${token}
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="copyBtn" style="padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Copy Authorization Header
                </button>
                <button id="copyTokenBtn" style="padding: 10px 20px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Copy Token Only
                </button>
                <button id="closeBtn" style="padding: 10px 20px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(popup);
        
        document.getElementById('copyBtn').addEventListener('click', () => {
            navigator.clipboard.writeText(`Bearer ${token}`)
                .then(() => alert('✅ Authorization header copied to clipboard!'))
                .catch(() => prompt('Copy this text:', `Bearer ${token}`));
        });
        
        document.getElementById('copyTokenBtn').addEventListener('click', () => {
            navigator.clipboard.writeText(token)
                .then(() => alert('✅ Token copied to clipboard!'))
                .catch(() => prompt('Copy this text:', token));
        });
        
        document.getElementById('closeBtn').addEventListener('click', () => {
            document.body.removeChild(popup);
        });
        
        // Close on escape
        document.addEventListener('keydown', function closeOnEscape(e) {
            if (e.key === 'Escape') {
                document.body.removeChild(popup);
                document.removeEventListener('keydown', closeOnEscape);
            }
        });
    }
})();

// Minified version for bookmarklet:
// javascript:(function(){fetch('http://localhost:8000/api/v1/auth/filebot-token').then(r=>r.ok?r.json():Promise.reject(`HTTP ${r.status}`)).then(d=>{const t=d.access_token;if(window.location.href.includes('localhost:8001/api/docs')){let f=!1;document.querySelectorAll('.btn.authorize').length>0&&(document.querySelectorAll('.btn.authorize')[0].click(),setTimeout(()=>{const e=document.querySelectorAll('input[type="text"][placeholder*="Bearer"], input[type="text"][placeholder*="Token"]');e.length>0&&(e[0].value=`Bearer ${t}`,f=!0,setTimeout(()=>{const e=document.querySelector('.auth-btn-wrapper .btn.authorize, .modal-footer .btn.authorize');e&&e.click()},100))},300));try{const e=JSON.parse(localStorage.getItem('swagger-ui')||'{}');e.authorized&&e.authorized.Bearer&&(e.authorized.Bearer.value=`Bearer ${t}`,localStorage.setItem('swagger-ui',JSON.stringify(e)),f=!0)}catch(e){console.log('Could not access localStorage:',e)}window.ui&&window.ui.authActions&&try{window.ui.authActions.authorize({Bearer:{name:'Bearer',value:`Bearer ${t}`}}),f=!0}catch(e){console.log('Swagger UI authActions not available:',e)}f?alert('✅ Token auto-filled successfully!\n\nYou can now use the FileBot API docs with the token.'):showPopup(t,'FileBot API Docs detected but could not auto-fill. Please paste this token manually:')}else{confirm('Token fetched successfully!\n'+`Token: ${t.substring(0,30)}...\n\n`+'Do you want to open FileBot API Docs?')&&window.open('http://localhost:8001/api/docs','_blank')}}).catch(e=>alert(`Error fetching token: ${e.message}\n\nMake sure WebBot is running on port 8000.`));function showPopup(e,t='Token fetched successfully:'){const o=document.createElement('div');o.style.cssText='position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;border-radius:10px;box-shadow:0 0 20px rgba(0,0,0,0.3);z-index:999999;max-width:90%;width:500px;font-family:Arial,sans-serif;';o.innerHTML=`<h3 style="margin-top:0;color:#4CAF50;">🔐 FileBot Token</h3><p>${t}</p><div style="background:#f5f5f5;padding:15px;border-radius:5px;margin:15px 0;word-break:break-all;font-family:monospace;">Bearer ${e}</div><div style="display:flex;gap:10px;justify-content:flex-end;"><button id="copyBtn" style="padding:10px 20px;background:#4CAF50;color:white;border:none;border-radius:5px;cursor:pointer;">Copy Authorization Header</button><button id="copyTokenBtn" style="padding:10px 20px;background:#2196F3;color:white;border:none;border-radius:5px;cursor:pointer;">Copy Token Only</button><button id="closeBtn" style="padding:10px 20px;background:#f44336;color:white;border:none;border-radius:5px;cursor:pointer;">Close</button></div>`;document.body.appendChild(o);document.getElementById('copyBtn').addEventListener('click',()=>{navigator.clipboard.writeText(`Bearer ${e}`).then(()=>alert('✅ Authorization header copied to clipboard!')).catch(()=>prompt('Copy this text:',`Bearer ${e}`))});document.getElementById('copyTokenBtn').addEventListener('click',()=>{navigator.clipboard.writeText(e).then(()=>alert('✅ Token copied to clipboard!')).catch(()=>prompt('Copy this text:',e))});document.getElementById('closeBtn').addEventListener('click',()=>{document.body.removeChild(o)});document.addEventListener('keydown',function n(r){'Escape'===r.key&&(document.body.removeChild(o),document.removeEventListener('keydown',n))})}})();