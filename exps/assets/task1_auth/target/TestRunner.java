
import com.example.*;

public class TestRunner {
    static int passed = 0;
    static int failed = 0;

    static void assertEquals(Object expected, Object actual, String msg) {
        if (expected == null ? actual == null : expected.equals(actual)) {
            passed++;
        } else {
            System.out.println("FAIL: " + msg + " - expected: " + expected + " got: " + actual);
            failed++;
        }
    }

    static void assertThrows(Class<?> exClass, Runnable r, String msg) {
        try {
            r.run();
            System.out.println("FAIL: " + msg + " - expected exception " + exClass.getSimpleName() + " but none thrown");
            failed++;
        } catch (Exception e) {
            if (e.getClass() == exClass) {
                passed++;
            } else {
                System.out.println("FAIL: " + msg + " - expected " + exClass.getSimpleName() + " but got " + e.getClass().getSimpleName() + ": " + e.getMessage());
                failed++;
            }
        }
    }

    public static void main(String[] args) {
        // Test 1: Authenticated user returns name
        UserController authController = new UserController(new UserService() {
            @Override
            public User getCurrentUser() {
                return new User("Alice");
            }
        });
        assertEquals("Alice", authController.getUserName(), "Authenticated user should return name");

        // Test 2: Anonymous user throws IllegalStateException
        UserController anonController = new UserController(new UserService());
        assertThrows(IllegalStateException.class,
            () -> anonController.getUserName(),
            "Anonymous user should get IllegalStateException, not NPE");

        // Test 3: Edge case - user with empty name
        UserController emptyNameController = new UserController(new UserService() {
            @Override
            public User getCurrentUser() {
                return new User("");
            }
        });
        assertEquals("", emptyNameController.getUserName(), "User with empty name should return empty string");

        // Test 4: UserService itself returns null (should also be handled)
        UserController nullServiceController = new UserController(null);
        assertThrows(NullPointerException.class,
            () -> nullServiceController.getUserName(),
            "Null UserService should throw NPE, not silent failure");

        System.out.println("\n=== RESULTS: " + passed + " passed, " + failed + " failed ===");
    }
}
