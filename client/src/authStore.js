export const authStore = {
  // We no longer store the JWT token in localStorage for security reasons.
  // The backend now issues an HttpOnly cookie that the browser sends automatically.
  
  getUser: () => JSON.parse(localStorage.getItem('vm_user') || 'null'),
  
  setAuth: (user) => {
    localStorage.setItem('vm_user', JSON.stringify(user));
  },
  
  clearAuth: () => {
    localStorage.removeItem('vm_user');
  },
  
  // getAuthHeaders is deprecated, use fetchWithAuth from apiService.js instead
};
