export const authStore = {
  getToken: () => localStorage.getItem('vm_token'),
  getUser: () => JSON.parse(localStorage.getItem('vm_user') || 'null'),
  setAuth: (token, user) => {
    localStorage.setItem('vm_token', token);
    localStorage.setItem('vm_user', JSON.stringify(user));
  },
  clearAuth: () => {
    localStorage.removeItem('vm_token');
    localStorage.removeItem('vm_user');
  },
  getAuthHeaders: () => ({
    'Authorization': `Bearer ${localStorage.getItem('vm_token')}`,
    'Content-Type': 'application/json'
  })
};
