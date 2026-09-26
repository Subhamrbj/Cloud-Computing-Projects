import React from 'react';
import {Play,Pause,Droplets,Sun} from 'lucide-react';
import {api} from './api';
export default function SimulationControls({device,busy,action}){
 if(!device||device.mode!=='virtual')return null;
 const run=(value,message)=>action(()=>api(`/devices/${device.device_id}/simulation`,{method:'POST',body:JSON.stringify({action:value})}),message);
 return <section className="simulation-bar" aria-label="Virtual sensor controls"><div><span className="eyebrow">BUILT-IN SIMULATION</span><strong>{device.simulation_running?'Your virtual sensor is running':'Your virtual sensor is paused'}</strong><p>Watch soil dry and recover after watering. Controls affect this plant only.</p></div><div className="simulation-buttons"><button className="outline" disabled={busy} onClick={()=>run(device.simulation_running?'pause':'start',device.simulation_running?'Simulation paused':'Simulation started')}>{device.simulation_running?<Pause size={16}/>:<Play size={16}/>} {device.simulation_running?'Pause':'Start'}</button><button className="outline" disabled={busy} onClick={()=>run('dry','Dry-soil reading sent. Safety rules still apply.')}><Sun size={16}/> Simulate dry soil</button><button className="outline" disabled={busy} onClick={()=>run('refill','Virtual tank refilled')}><Droplets size={16}/> Refill tank</button></div></section>;
}
