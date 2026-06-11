
package com.example;

public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * Returns the name of the currently authenticated user.
     *
     * @return the current user's name
     * @throws IllegalStateException if no user is authenticated (anonymous)
     */
    public String getUserName() {
        User user = userService.getCurrentUser();
        if (user == null) {
            throw new IllegalStateException("Anonymous user cannot access username");
        }
        return user.getName();
    }
}
