package com.workflowradar.fde;
import org.springframework.stereotype.Repository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import tools.jackson.databind.json.JsonMapper;

@Repository
public class JobRepository {
 private final String url;
 private final JsonMapper mapper=JsonMapper.builder().build();
 public record Submitted(boolean created,Map<String,Object> job){}
 public JobRepository(@Value("${fde.db.path:.build/fde-labs/spring.db}") String path)throws Exception{
  Path file=Path.of(path).toAbsolutePath();Files.createDirectories(file.getParent());url="jdbc:sqlite:"+file;
  try(var db=open();var stmt=db.createStatement()){
   int version=stmt.executeQuery("PRAGMA user_version").getInt(1);
   if(version!=0&&version!=1)throw new IllegalStateException("Unsupported jobs schema");
   String sql=new String(new ClassPathResource("db/migration/V1__jobs.sql").getInputStream().readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);
   for(String statement:sql.split(";"))if(!statement.isBlank())stmt.execute(statement);
  }
 }
 private Connection open()throws SQLException{var c=DriverManager.getConnection(url);try(var s=c.createStatement()){s.execute("PRAGMA busy_timeout=10000");}return c;}
 private Map<String,Object> row(ResultSet result)throws SQLException{
  var map=new LinkedHashMap<String,Object>();var meta=result.getMetaData();
  for(int i=1;i<=meta.getColumnCount();i++)map.put(meta.getColumnName(i),result.getObject(i));
  map.put("payload",mapper.readValue((String)map.get("payload"),Map.class));return map;
 }
 public Submitted submit(String tenant,String key,Map<String,Object> payload)throws Exception{
  String text=mapper.writeValueAsString(new TreeMap<>(payload));
  try(var db=open();var tx=db.createStatement()){
   tx.execute("BEGIN IMMEDIATE");
   try{
    try(var p=db.prepareStatement("SELECT * FROM jobs WHERE tenant=? AND key=?")){
     p.setString(1,tenant);p.setString(2,key);try(var rs=p.executeQuery()){if(rs.next()){
      if(!rs.getString("payload").equals(text))throw new IllegalArgumentException("idempotency_conflict");
      var result=new Submitted(false,row(rs));tx.execute("COMMIT");return result;
     }}
    }
    String id=UUID.randomUUID().toString();double now=System.currentTimeMillis()/1000.0;
    try(var p=db.prepareStatement("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")){
     Object[] values={id,tenant,key,text,"queued",null,0,0,0,3,now+3600,now,0,"0","0",null};
     for(int i=0;i<values.length;i++)p.setObject(i+1,values[i]);p.executeUpdate();
    }
    tx.execute("COMMIT");return new Submitted(true,get(tenant,id));
   }catch(Exception e){tx.execute("ROLLBACK");throw e;}
  }
 }
 public Map<String,Object> get(String tenant,String id)throws SQLException{
  try(var db=open();var p=db.prepareStatement("SELECT * FROM jobs WHERE tenant=? AND id=?")){
   p.setString(1,tenant);p.setString(2,id);try(var rs=p.executeQuery()){if(!rs.next())throw new NoSuchElementException("job_not_found");return row(rs);}
  }
 }
 public Map<String,Object> cancel(String tenant,String id)throws SQLException{
  try(var db=open();var p=db.prepareStatement("UPDATE jobs SET cancel_requested=1,status=CASE WHEN status IN ('queued','retry_wait') THEN 'cancelled' ELSE status END WHERE tenant=? AND id=? AND status IN ('queued','retry_wait','running')")){
   p.setString(1,tenant);p.setString(2,id);p.executeUpdate();
  }
  return get(tenant,id);
 }
}
