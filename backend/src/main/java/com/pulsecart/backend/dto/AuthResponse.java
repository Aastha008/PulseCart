package com.pulsecart.backend.dto;

import com.pulsecart.backend.entity.Role;

public record AuthResponse(
        String token,
        String tokenType,
        Long userId,
        String email,
        Role role,
        String firstName,
        String lastName
) {
    public static AuthResponse of(String token, Long userId, String email, Role role, String firstName, String lastName) {
        return new AuthResponse(token, "Bearer", userId, email, role, firstName, lastName);
    }
}
