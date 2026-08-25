
// ==============================
// Quantity Buttons
// ==============================

const qtyBoxes = document.querySelectorAll(".qty");

qtyBoxes.forEach(box => {

    const minus = box.children[0];
    const number = box.children[1];
    const plus = box.children[2];

    let qty = 1;

    plus.addEventListener("click", () => {
        qty++;
        number.innerText = qty;
    });

    minus.addEventListener("click", () => {

        if(qty > 1){
            qty--;
            number.innerText = qty;
        }

    });

});

// ==========================
// Shopping Cart Sidebar
// ==========================

const cartIcon = document.getElementById("cartIcon");
const cartSidebar = document.getElementById("cartSidebar");
const closeCart = document.getElementById("closeCart");
const cartOverlay = document.getElementById("cartOverlay");

if(cartIcon){

    cartIcon.addEventListener("click",()=>{

        cartSidebar.classList.add("active");

        cartOverlay.classList.add("active");

    });

}

if(closeCart){

    closeCart.addEventListener("click",()=>{

        cartSidebar.classList.remove("active");

        cartOverlay.classList.remove("active");

    });

}

if(cartOverlay){

    cartOverlay.addEventListener("click",()=>{

        cartSidebar.classList.remove("active");

        cartOverlay.classList.remove("active");

    });

}
// ==========================
// Shopping Cart System
// ==========================

let cart = JSON.parse(localStorage.getItem("cart")) || [];

const addCartButtons = document.querySelectorAll(".add-cart");
const cartItems = document.getElementById("cartItems");
const cartCount = document.getElementById("cartCount");
const cartSubtotal = document.getElementById("cartSubtotal");
const deliveryFee = document.getElementById("deliveryFee");
const taxAmount = document.getElementById("taxAmount");
const cartTotal = document.getElementById("cartTotal");
const menuToggle = document.querySelector(".menu-toggle");
const menu = document.querySelector(".menu");

menuToggle.addEventListener("click", () => {
    menu.classList.toggle("active");
});
// ==========================
// Professional Shopping Cart
// ==========================

let cart = JSON.parse(localStorage.getItem("cart")) || [];
const addCartButtons = document.querySelectorAll(".add-cart");
const cartItems = document.getElementById("cartItems");
const cartCount = document.getElementById("cartCount");
const cartTotal = document.getElementById("cartTotal");

addCartButtons.forEach(button => {

    button.addEventListener("click", () => {

        const name = button.dataset.name;
        const price = parseFloat(button.dataset.price);
const image = button.dataset.image;
        const existingItem = cart.find(item => item.name === name);

        if(existingItem){

            existingItem.quantity++;

        }else{

 cart.push({

    name:name,
    price:price,
    image:image,
    quantity:1

});
        }

        updateCart();

    });

});

function updateCart(){

    cartItems.innerHTML = "";

    let total = 0;

    if(cart.length===0){

        cartItems.innerHTML = "<p class='empty-cart'>Your cart is empty.</p>";

        cartCount.innerText = 0;
        cartTotal.innerText = "0.00";

        return;

    }

    cart.forEach((item,index)=>{

        const subtotal = item.price * item.quantity;

        total += subtotal;

        cartItems.innerHTML += `

        <div class="cart-item">

            <h4>${item.name}</h4>

            <p>$${item.price.toFixed(2)}</p>

            <div class="cart-qty">

                <button onclick="decreaseQuantity(${index})">−</button>

                <span>${item.quantity}</span>

                <button onclick="increaseQuantity(${index})">+</button>

            </div>

            <h5>$${subtotal.toFixed(2)}</h5>

            <button class="remove-btn" onclick="removeItem(${index})">
                Remove
            </button>

        </div>

        `;

    });

    cartCount.innerText = cart.length;

    const delivery = 5;
const tax = total * 0.05;
const grandTotal = total + delivery + tax;

cartSubtotal.innerText = total.toFixed(2);
taxAmount.innerText = tax.toFixed(2);
deliveryFee.innerText = delivery.toFixed(2);
cartTotal.innerText = grandTotal.toFixed(2);
    localStorage.setItem("cart", JSON.stringify(cart));

}

function increaseQuantity(index){

    cart[index].quantity++;

    updateCart();

}

function decreaseQuantity(index){

    if(cart[index].quantity>1){

        cart[index].quantity--;

    }else{

        cart.splice(index,1);

    }

    updateCart();

}

function removeItem(index){

    cart.splice(index,1);

    updateCart();

}
// Load cart when page opens
updateCart();
// ==========================
// Add To Cart
// ==========================

let cart = [];

const cartItems = document.getElementById("cartItems");
const cartCount = document.getElementById("cartCount");
const cartTotal = document.getElementById("cartTotal");

const addButtons = document.querySelectorAll(".add-cart");

addButtons.forEach(button => {

    button.addEventListener("click", () => {

        const card = button.closest(".food-card");

        const name = card.querySelector("h4").innerText;
        const price = parseFloat(
            card.querySelector(".menu-bottom h3").innerText.replace("$","")
        );

        cart.push({
            name,
            price
        });

        updateCart();

    });

});

function updateCart(){

    cartItems.innerHTML="";

    let total=0;

    cart.forEach((item,index)=>{

        total += item.price;

        cartItems.innerHTML += `
        <div class="cart-item">

            <div>
                <h4>${item.name}</h4>
                <p>$${item.price.toFixed(2)}</p>
            </div>

            <button class="remove-item" onclick="removeItem(${index})">
                ✖
            </button>

        </div>
        `;

    });

    if(cart.length===0){

        cartItems.innerHTML=
        "<p class='empty-cart'>Your cart is empty.</p>";

    }

    cartCount.innerText=cart.length;

    cartTotal.innerText=total.toFixed(2);

}

function removeItem(index){

    cart.splice(index,1);

    updateCart();

}