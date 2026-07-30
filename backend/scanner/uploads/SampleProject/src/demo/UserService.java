package demo;

import java.util.ArrayList;
import java.util.List;

public class UserService {

    private String currentUser;
    private String currentPassword;
    private String currentToken;
    private List<String> loginHistory = new ArrayList<>();

    // Mirrors the login() example from the project proposal: this one method
    // is doing validation + authentication + token generation + notification.
    public String login(String username, String password, String ipAddress, boolean rememberMe) {
        if (username == null || username.isEmpty()) {
            System.out.println("Username is required");
            return null;
        }
        if (password == null || password.length() < 8) {
            System.out.println("Password must be at least 8 characters");
            return null;
        }
        currentUser = username;
        currentPassword = password;

        boolean authenticated = false;
        if (currentPassword.equals(password)) {
            authenticated = true;
        }
        if (!authenticated) {
            System.out.println("Authentication failed for " + username);
            return null;
        }

        String token = username + ":" + System.currentTimeMillis();
        currentToken = token;

        System.out.println("Sending login notification email to " + username);
        System.out.println("Login detected from IP: " + ipAddress);
        loginHistory.add(username + " logged in from " + ipAddress);

        if (rememberMe) {
            System.out.println("Extending session for " + username);
        }

        return token;
    }

    // Deliberately duplicated logic (identical body to registerAdmin below,
    // aside from the log message) to exercise DuplicateCodeRule.
    public boolean registerUser(String username, String password) {
        if (username == null || username.isEmpty()) {
            return false;
        }
        if (password == null || password.length() < 8) {
            return false;
        }
        currentUser = username;
        currentPassword = password;
        System.out.println("User registered: " + username);
        return true;
    }

    public boolean registerAdmin(String username, String password) {
        if (username == null || username.isEmpty()) {
            return false;
        }
        if (password == null || password.length() < 8) {
            return false;
        }
        currentUser = username;
        currentPassword = password;
        System.out.println("User registered: " + username);
        return true;
    }

    public String getCurrentUser() {
        return currentUser;
    }

    public String getCurrentToken() {
        return currentToken;
    }

    public List<String> getLoginHistory() {
        return loginHistory;
    }
}
