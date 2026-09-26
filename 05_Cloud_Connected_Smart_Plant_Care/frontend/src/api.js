export function setToken(){}
export async function api(path, options={}){
  const response = await fetch('/api'+path,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...options.headers}});
  let data;
  try{data=await response.json();}catch{throw new Error('Server returned an unexpected response');}
  if(!response.ok) { const error=new Error(typeof data.detail==='string'?data.detail:'Please check the submitted values');error.status=response.status;throw error; }
  return data;
}
