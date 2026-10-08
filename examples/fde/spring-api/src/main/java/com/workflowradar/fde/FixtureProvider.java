package com.workflowradar.fde;
import org.springframework.stereotype.Component;
import java.util.*;
@Component
public class FixtureProvider {
 private final SpringAiProvider optional;
 public FixtureProvider(org.springframework.beans.factory.ObjectProvider<SpringAiProvider> provider){optional=provider.getIfAvailable();}
 public String mode(){return optional==null?"fixture":"ollama";}
 public Map<String,Object> query(String tenant,Map<String,Object> payload){
  if(!payload.keySet().equals(Set.of("query"))||!(payload.get("query") instanceof String query)||query.isBlank()||query.length()>4000)throw new IllegalArgumentException("invalid_schema");
  if(!query.toLowerCase(Locale.ROOT).contains("refund"))return Map.of("status","insufficient_evidence","answer","","citations",List.of());
  String id="policy-"+tenant;
  if(optional!=null)return optional.generate(id,query);
  return Map.of("status","answered","answer","Synthetic refund policy for "+tenant,"citations",List.of(Map.of("id",id,"version",1)));
 }
}
