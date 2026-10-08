package com.workflowradar.fde;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class AnswerValidationTest {
 @Test void forgedOrMalformedModelAnswerFailsClosed(){
  assertThrows(IllegalArgumentException.class,()->SpringAiProvider.validate("{\"status\":\"answered\",\"answer\":\"secret\",\"citations\":[{\"id\":\"policy-two\",\"version\":1}]}","policy-one"));
  assertThrows(IllegalArgumentException.class,()->SpringAiProvider.validate("{}","policy-one"));
  assertEquals("answered",SpringAiProvider.validate("{\"status\":\"answered\",\"answer\":\"synthetic\",\"citations\":[{\"id\":\"policy-one\",\"version\":1}]}","policy-one").get("status"));
 }
}
