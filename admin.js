// =====================================
// Admin Login
// =====================================

const adminForm = document.getElementById("adminLoginForm");

if (adminForm) {

    adminForm.addEventListener("submit", (e) => {

        e.preventDefault();

        const email =
            document.getElementById("adminEmail").value.trim();

        const password =
            document.getElementById("adminPassword").value.trim();

        const button =
            document.getElementById("adminLoginBtn");


        // ADMIN CREDENTIALS

        const ADMIN_EMAIL =
            "admin@testyrestaurant.com";

        const ADMIN_PASSWORD =
            "admin123";


        // CHECK EMAIL

        if (email !== ADMIN_EMAIL) {

            showToast("Invalid Admin ID.");

            return;

        }


        // CHECK PASSWORD

        if (password !== ADMIN_PASSWORD) {

            showToast("Incorrect Admin Password.");

            return;

        }


        // LOGIN SUCCESS

        button.innerHTML = "Signing In...";

        button.disabled = true;


        // SAVE ADMIN ROLE

        localStorage.setItem(
            "userRole",
            "admin"
        );

        localStorage.setItem(
            "adminEmail",
            email
        );


        setTimeout(() => {

            showToast(
                "Admin Login Successful!"
            );


            window.location.href =
                "dashboard.html";


        }, 1000);

    });

}