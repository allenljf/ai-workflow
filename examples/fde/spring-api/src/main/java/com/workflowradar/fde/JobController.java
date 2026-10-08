package com.workflowradar.fde;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import jakarta.servlet.http.HttpServletRequest;
import java.util.*;
@RestController
public class JobController {
 private final JobService service;private final FixtureProvider provider;
 public JobController(JobService service,FixtureProvider provider){this.service=service;this.provider=provider;}
 private String tenant(HttpServletRequest request){return (String)request.getAttribute("tenant");}
 @GetMapping("/health")public Map<String,String> health(){return Map.of("status","ok","provider",provider.mode());}
 @PostMapping("/jobs")public ResponseEntity<Map<String,Object>> submit(HttpServletRequest request,@RequestHeader(value="Idempotency-Key",required=false)String key,@RequestBody Map<String,Object> payload)throws Exception{
  var result=service.submit(tenant(request),key,payload);return ResponseEntity.status(result.created()?201:200).body(result.job());
 }
 @GetMapping("/jobs/{id}")public Map<String,Object> get(HttpServletRequest request,@PathVariable String id)throws Exception{return service.get(tenant(request),id);}
 @PostMapping("/jobs/{id}/cancel")public Map<String,Object> cancel(HttpServletRequest request,@PathVariable String id)throws Exception{return service.cancel(tenant(request),id);}
 @PostMapping("/rag/query")public Map<String,Object> query(HttpServletRequest request,@RequestBody Map<String,Object> payload){return provider.query(tenant(request),payload);}
 @ExceptionHandler(NoSuchElementException.class)public ResponseEntity<Map<String,String>> missing(){return ResponseEntity.status(404).body(Map.of("error","job_not_found"));}
 @ExceptionHandler(IllegalArgumentException.class)public ResponseEntity<Map<String,String>> invalid(IllegalArgumentException error){String code="idempotency_conflict".equals(error.getMessage())?"idempotency_conflict":"invalid_schema";return ResponseEntity.status(code.equals("idempotency_conflict")?409:400).body(Map.of("error",code));}
}
