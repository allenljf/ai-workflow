package com.workflowradar.fde;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.filter.OncePerRequestFilter;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

@Component
public class PrincipalFilter extends OncePerRequestFilter {
 private final String one,two;
 public PrincipalFilter(@Value("${fde.auth.token-one:}")String one,@Value("${fde.auth.token-two:}")String two){
  if(!one.isEmpty()&&one.equals(two))throw new IllegalArgumentException("Distinct tenant credentials required");this.one=one;this.two=two;
 }
 private boolean matches(String actual,String expected){return !expected.isEmpty()&&MessageDigest.isEqual(actual.getBytes(StandardCharsets.UTF_8),expected.getBytes(StandardCharsets.UTF_8));}
 @Override protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain)throws IOException,ServletException{
  if(req.getMethod().equals("GET")&&req.getRequestURI().equals("/health")){chain.doFilter(req,res);return;}
  String auth=req.getHeader("Authorization"),tenant=null;
  if(auth!=null&&auth.startsWith("Bearer ")){String token=auth.substring(7);if(matches(token,one))tenant="one";else if(matches(token,two))tenant="two";}
  if(tenant==null){res.setStatus(401);res.setContentType("application/json");res.getWriter().write("{\"error\":\"unauthenticated\"}");return;}
  req.setAttribute("tenant",tenant);chain.doFilter(req,res);
 }
}
