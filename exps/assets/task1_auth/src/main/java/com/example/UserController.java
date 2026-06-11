package com.example;

public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * BUG: This method crashes when user is null (anonymous user).
     */
    public String getUserName() {
        User user = userService.getCurrentUser();
        if (user == null) {
            throw new IllegalStateException("No authenticated user found");
        }
        return user.getName();
    }
}
