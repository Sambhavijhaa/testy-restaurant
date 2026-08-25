// =====================================================
// TESTY RESTAURANT AUTHENTICATION
// =====================================================


// REGISTER USER
function registerUser(name, email, password) {

    const user = {
        name: name,
        email: email,
        password: password
    };

    localStorage.setItem(
        "testyUser",
        JSON.stringify(user)
    );

    localStorage.setItem(
        "testyLoggedIn",
        "true"
    );
}


// LOGIN USER
function loginUser(email, password) {

    const savedUser =
        JSON.parse(
            localStorage.getItem("testyUser")
        );

    if (!savedUser) {

        return {
            success: false,
            message: "No account found. Please register first."
        };

    }


    if (
        savedUser.email === email &&
        savedUser.password === password
    ) {

        localStorage.setItem(
            "testyLoggedIn",
            "true"
        );

        return {
            success: true,
            message: "Login successful."
        };

    }


    return {
        success: false,
        message: "Incorrect email or password."
    };

}


// LOGOUT
function logoutUser() {

    localStorage.removeItem(
        "testyLoggedIn"
    );

    window.location.href =
        "auth/login.html";

}


// GET CURRENT USER
function getCurrentUser() {

    const user =
        JSON.parse(
            localStorage.getItem("testyUser")
        );

    return user;

}


// CHECK LOGIN
function isLoggedIn() {

    return (
        localStorage.getItem(
            "testyLoggedIn"
        ) === "true"
    );

}