let token = '';
export function setToken(value){token=value;}
export async function api(path, options={}){
  const response = await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json',Authorization:'Bearer '+token,...options.headers}});
  let data;
  try{data=await response.json();}catch{throw new Error('Server returned an unexpected response');}
  if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Please check the submitted values');
  return data;
}
