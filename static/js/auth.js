const extractErrorMessage = (data) => {
    if (!data) return null;
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) {
        return data.detail
            .map(item => item.msg || item.message || JSON.stringify(item))
            .join(', ');
    }
    if (data.error) {
        if (typeof data.error === 'string') return data.error;
        if (data.error.message) return data.error.message;
    }
    return data.message || null;
};

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginError = document.getElementById('loginError');
    const registerForm = document.getElementById('eliteProfileForm');

    // Login Logic
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const originalBtnContent = submitBtn.innerHTML;

            // Reset error
            if (loginError) {
                loginError.classList.add('hidden');
                loginError.textContent = '';
            }

            // Loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="animate-pulse">Signing in...</span>';

            try {
                const payload = new URLSearchParams();
                payload.append('username', email);
                payload.append('password', password);

                const response = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: payload.toString()
                });

                const data = await response.json();

                if (response.ok) {
                    // Store token
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('token_type', data.token_type);
                    
                    // Redirect to dashboard or home
                    window.location.href = '/dashboard';
                } else {
                    throw new Error(extractErrorMessage(data) || 'Login failed');
                }
            } catch (error) {
                if (loginError) {
                    loginError.textContent = error.message;
                    loginError.classList.remove('hidden');
                } else {
                    alert(error.message);
                }
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnContent;
            }
        });
    }

    // Registration Logic
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(registerForm);
            const name = formData.get('fullName');
            const email = formData.get('email');
            const password = formData.get('password');
            const role = formData.get('role');
            const goals = formData.get('goals');

            // Collect industries (custom UI)
            const industries = Array.from(document.querySelectorAll('.elite-checkbox:checked')).map(c => c.value);
            
            // Collect skills (custom UI)
            const skills = Array.from(document.querySelectorAll('.elite-skill-pill.selected'))
                .map(p => p.getAttribute('data-skill'))
                .filter(Boolean);
            
            // Basic validation
            if (!name || !email || !password) {
                alert('Please fill in all required fields');
                return;
            }

            const submitBtn = registerForm.querySelector('button[type="submit"]');
            const originalBtnContent = submitBtn ? submitBtn.innerHTML : '';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="animate-pulse">Creating Profile...</span>';
            }

            try {
                const response = await fetch('/api/v1/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: name,
                        email: email,
                        password: password,
                        role: role,
                        goals: goals,
                        industries: industries,
                        skills: skills
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    // Store token
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('token_type', data.token_type);
                    
                    // Redirect to dashboard
                    window.location.href = '/dashboard';
                } else {
                    throw new Error(extractErrorMessage(data) || 'Registration failed');
                }
            } catch (error) {
                alert(error.message);
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnContent;
                }
            }
        });
    }
});
