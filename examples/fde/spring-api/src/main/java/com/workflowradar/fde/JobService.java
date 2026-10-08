package com.workflowradar.fde;
import org.springframework.stereotype.Service;
import java.util.*;
@Service
public class JobService {
 private final JobRepository repository;
 public JobService(JobRepository repository){this.repository=repository;}
 public JobRepository.Submitted submit(String tenant,String key,Map<String,Object> payload)throws Exception{
  if(key==null||key.isBlank()||key.length()>200||!payload.keySet().equals(Set.of("operation"))||!(payload.get("operation") instanceof String operation)||!Set.of("import","analyze").contains(operation))throw new IllegalArgumentException("invalid_schema");
  return repository.submit(tenant,key,payload);
 }
 public Map<String,Object> get(String tenant,String id)throws Exception{return repository.get(tenant,id);}
 public Map<String,Object> cancel(String tenant,String id)throws Exception{return repository.cancel(tenant,id);}
}
