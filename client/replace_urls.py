import re

with open('src/App.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

injection = """
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE = IS_LOCAL ? 'http://localhost:8000' : `https://${import.meta.env.VITE_API_DOMAIN || 'api.vaultmind.systems'}`;
"""

code = code.replace(
    'import { LoadingShimmer } from "./components/LoadingShimmer.jsx";',
    'import { LoadingShimmer } from "./components/LoadingShimmer.jsx";\n' + injection
)

# Replace fetch URLs: "https://api.vaultmind.systems/api/..." -> `${API_BASE}/api/...`
code = re.sub(r'"https://api\.vaultmind\.systems(/api/[^"]+)"', r'`${API_BASE}\1`', code)

# Replace template literals: `https://api.vaultmind.systems/api/...` -> `${API_BASE}/api/...`
code = re.sub(r'`https://api\.vaultmind\.systems(/api/[^`]+)`', r'`${API_BASE}\1`', code)

with open('src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Replacement successful!")
