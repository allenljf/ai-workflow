package com.workflowradar.fde;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.beans.factory.annotation.Value;
import java.net.URI;
import java.net.http.*;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(classes=Application.class,webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT,properties={"fde.auth.token-one=synthetic-one","fde.auth.token-two=synthetic-two","fde.db.path=target/test-jobs.db","server.address=127.0.0.1"})
class JobApiTest {
 @Value("${local.server.port}") int port;
 HttpResponse<String> call(String method,String path,String token,String key,String body)throws Exception{
  var b=HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+port+path)).header("Content-Type","application/json");
  if(token!=null)b.header("Authorization","Bearer "+token);
  if(key!=null)b.header("Idempotency-Key",key);
  b.method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(body));
  return HttpClient.newHttpClient().send(b.build(),HttpResponse.BodyHandlers.ofString());
 }
 @Test void authAndTenantIsolation()throws Exception{
  assertEquals(200,call("GET","/health",null,null,null).statusCode());
  assertEquals(401,call("POST","/jobs",null,"a","{\"operation\":\"import\"}").statusCode());
  var created=call("POST","/jobs","synthetic-one","test-a-"+java.util.UUID.randomUUID(),"{\"operation\":\"import\"}");assertEquals(201,created.statusCode());
  var id=created.body().split("\"id\":\"")[1].split("\"")[0];
  assertEquals(404,call("GET","/jobs/"+id,"synthetic-two",null,null).statusCode());
  assertEquals(200,call("GET","/jobs/"+id,"synthetic-one",null,null).statusCode());
 }
 @Test void idempotencyAndSchema()throws Exception{
  var key="key-"+java.util.UUID.randomUUID();
  var first=call("POST","/jobs","synthetic-one",key,"{\"operation\":\"import\"}");assertEquals(201,first.statusCode());
  var again=call("POST","/jobs","synthetic-one",key,"{\"operation\":\"import\"}");assertEquals(200,again.statusCode());assertEquals(first.body(),again.body());
  assertEquals(409,call("POST","/jobs","synthetic-one",key,"{\"operation\":\"analyze\"}").statusCode());
  assertEquals(400,call("POST","/jobs","synthetic-one","schema","{\"tenant\":\"two\",\"operation\":\"import\"}").statusCode());
  var id=first.body().split("\"id\":\"")[1].split("\"")[0];
  assertEquals(200,call("POST","/jobs/"+id+"/cancel","synthetic-one",null,"{}").statusCode());
  assertTrue(call("GET","/jobs/"+id,"synthetic-one",null,null).body().contains("cancelled"));
 }
 @Test void ragSchemaAndNoEvidence()throws Exception{
  assertEquals(400,call("POST","/rag/query","synthetic-one",null,"{\"tenant\":\"two\",\"query\":\"refund\"}").statusCode());
  assertTrue(call("POST","/rag/query","synthetic-one",null,"{\"query\":\"unknown\"}").body().contains("insufficient_evidence"));
  var answer=call("POST","/rag/query","synthetic-one",null,"{\"query\":\"refund\"}");assertEquals(200,answer.statusCode());assertTrue(answer.body().contains("policy-one"));assertFalse(answer.body().contains("policy-two"));
 }
}
