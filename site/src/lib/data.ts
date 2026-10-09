import json from '../generated/radar.json';
export interface RadarEvent {id:string;title:string;url:string;published_at:string|null;updated_at?:string|null;fetched_at:string;entity:string|null;version:string|null;sources:{id:string;url:string}[];topics:string[];trust_tier:string;status:string}
export interface RadarSource {id:string;last_attempt:string|null;last_success:string|null;status:string}
export interface RadarData {update_status?:{ai_enabled:boolean;next_due_at:string|null;knowledge?:{enabled:boolean;last_searched_at:string|null;next_search_due_at:string|null};fde:{collected_at:string|null;enriched_at:string|null;reviewed_at:string|null}};generated_at:string;last_enriched_at:string|null;last_reviewed_at:string|null;events:RadarEvent[];sources:RadarSource[]}
export const data = json as RadarData;
export const href=(path='')=>import.meta.env.BASE_URL.replace(/\/?$/,'/')+path;
export const date=(value:string|null)=>value?new Intl.DateTimeFormat('zh-TW',{timeZone:'Asia/Taipei',dateStyle:'medium',timeStyle:'short'}).format(new Date(value)):'尚無紀錄';
