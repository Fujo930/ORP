
package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class UserControllerTest {

    @Test
    void testGetUserName_withAuthenticatedUser() {
        UserService service = new UserService() {
            @Override
            public User getCurrentUser() {
                return new User("Alice");
            }
        };
        UserController controller = new UserController(service);
        assertEquals("Alice", controller.getUserName());
    }

    @Test
    void testGetUserName_withAnonymousUser() {
        UserController controller = new UserController(new UserService());
        // This currently throws NullPointerException
        // Fix should handle null user gracefully
        assertThrows(IllegalStateException.class,
            () -> controller.getUserName(),
            "Anonymous user should get IllegalStateException, not NPE"
        );
    }
}
