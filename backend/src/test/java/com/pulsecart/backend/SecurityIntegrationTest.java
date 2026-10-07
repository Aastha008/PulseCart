package com.pulsecart.backend;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pulsecart.backend.dto.AuthRequest;
import com.pulsecart.backend.dto.CreateOrderRequest;
import com.pulsecart.backend.dto.CreateProductRequest;
import com.pulsecart.backend.dto.RegisterRequest;
import com.pulsecart.backend.entity.Role;
import com.pulsecart.backend.entity.User;
import com.pulsecart.backend.repository.UserRepository;
import com.pulsecart.backend.security.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.util.List;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
public class SecurityIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private ObjectMapper objectMapper;

    private String customerToken;
    private String adminToken;

    @BeforeEach
    void setUp() {
        User customer = userRepository.findByEmail("test-customer@example.com").orElseGet(() ->
                userRepository.save(new User("test-customer@example.com", passwordEncoder.encode("Pass1234!"), "John", "Doe", Role.ROLE_CUSTOMER))
        );

        User admin = userRepository.findByEmail("test-admin@example.com").orElseGet(() ->
                userRepository.save(new User("test-admin@example.com", passwordEncoder.encode("AdminPass123!"), "Super", "Admin", Role.ROLE_ADMIN))
        );

        customerToken = "Bearer " + jwtService.generateToken(customer);
        adminToken = "Bearer " + jwtService.generateToken(admin);
    }

    @Test
    @DisplayName("Registration: creates customer account with hashed password and returns JWT")
    void testCustomerRegistration() throws Exception {
        RegisterRequest registerReq = new RegisterRequest(
                "newuser@example.com",
                "StrongPassword123!",
                "Alice",
                "Wonderland"
        );

        mockMvc.perform(post("/api/v1/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(registerReq)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.token").isNotEmpty())
                .andExpect(jsonPath("$.email").value("newuser@example.com"))
                .andExpect(jsonPath("$.role").value("ROLE_CUSTOMER"));
    }

    @Test
    @DisplayName("Login: valid credentials return JWT token")
    void testCustomerLogin() throws Exception {
        AuthRequest authReq = new AuthRequest("test-customer@example.com", "Pass1234!");

        mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(authReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").isNotEmpty())
                .andExpect(jsonPath("$.email").value("test-customer@example.com"));
    }

    @Test
    @DisplayName("Login: invalid credentials return 401 Unauthorized")
    void testCustomerLoginInvalidCredentials() throws Exception {
        AuthRequest authReq = new AuthRequest("test-customer@example.com", "WrongPassword!");

        mockMvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(authReq)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("Unauthenticated request to protected order endpoint returns 401 Unauthorized")
    void testUnauthenticatedAccessRejected() throws Exception {
        CreateOrderRequest request = new CreateOrderRequest(List.of(), "CREDIT_CARD");

        mockMvc.perform(post("/api/v1/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("Customer attempting to access admin endpoint returns 403 Forbidden")
    void testCustomerCannotAccessAdminEndpoints() throws Exception {
        CreateProductRequest request = new CreateProductRequest(
                "NEW-SKU-999", "Admin Product", "Desc", "Electronics",
                new BigDecimal("100.00"), new BigDecimal("50.00"), 10
        );

        mockMvc.perform(post("/api/v1/admin/products")
                        .header("Authorization", customerToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isForbidden());
    }

    @Test
    @DisplayName("Admin can access admin endpoint to create products")
    void testAdminCanCreateProduct() throws Exception {
        CreateProductRequest request = new CreateProductRequest(
                "ADMIN-SKU-888", "Server Rack", "Desc", "Electronics",
                new BigDecimal("499.00"), new BigDecimal("250.00"), 5
        );

        mockMvc.perform(post("/api/v1/admin/products")
                        .header("Authorization", adminToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.sku").value("ADMIN-SKU-888"))
                .andExpect(jsonPath("$.stock").value(5));
    }
}
