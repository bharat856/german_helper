const base=import.meta.env.VITE_API_URL||'http://localhost:8000';
export async function api<T>(path:string, options:RequestInit={}){const r=await fetch(base+path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options}); if(!r.ok) throw new Error((await r.json().catch(()=>({detail:'Request failed'}))).detail); return r.json() as Promise<T>}
