
let movies = [];
let selectedMovie = null;
let selectedSeats = new Set();
let authMode = "login";

const $ = id => document.getElementById(id);

const token = () => localStorage.getItem("showtime_token");

function toast(msg) {
    $("toast").textContent = msg;
    $("toast").classList.add("show");

    setTimeout(() => {
        $("toast").classList.remove("show");
    }, 2800);
}

async function api(url, opts = {}) {
    opts.headers = {
        ...(opts.headers || {}),
        "Content-Type": "application/json"
    };

    if (token()) {
        opts.headers.Authorization = "Bearer " + token();
    }

    const response = await fetch(url, opts);

    const data = await response.json().catch(() => ({
        message: "Unexpected server response"
    }));

    if (!response.ok) {
        throw new Error(data.message || "Request failed");
    }

    return data;
}


// MOVIES

function posterCard(m) {
    const img = m.poster_url
        ? `<img src="${m.poster_url}" alt="${m.title} poster"
        onerror="this.remove();this.nextElementSibling.style.display='grid'">`
        : "";

    return `
    <article class="movie-card" data-id="${m.id}">
        <div class="poster">
            ${img}
            <div class="poster-placeholder"
                style="${m.poster_url ? 'display:none' : ''}">
                ${m.title}
                <small>PAWAN KALYAN · ${m.year || ""}</small>
            </div>
        </div>

        <div class="movie-info">
            <h3>${m.title}</h3>
            <p>${m.year || ""} · Telugu</p>
            <p class="genre">${m.genre || ""}</p>
        </div>
    </article>`;
}

async function loadMovies() {
    try {
        movies = await api("/api/movies");
        renderMovies(movies);
    } catch (e) {
        toast(e.message);
    }
}

function renderMovies(list) {
    $("featured").innerHTML = list
        .filter(m => m.featured)
        .map(posterCard)
        .join("");

    $("allMovies").innerHTML = list
        .map(posterCard)
        .join("");

    document.querySelectorAll(".movie-card").forEach(card => {
        card.addEventListener("click", () => {
            openBooking(Number(card.dataset.id));
        });
    });
}

$("search").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();

    renderMovies(
        movies.filter(m => m.title.toLowerCase().includes(q))
    );
});


// LOGIN / SIGNUP

function updateAuthUI() {
    if (!token()) {
        $("welcome").textContent = "";
        $("authBtn").textContent = "Sign in";
        return;
    }

    api("/api/me")
        .then(user => {
            $("welcome").textContent =
                "Hi, " + user.name.split(" ")[0];

            $("authBtn").textContent = "My bookings";
        })
        .catch(() => {
            localStorage.removeItem("showtime_token");
            $("welcome").textContent = "";
            $("authBtn").textContent = "Sign in";
        });
}

function setAuthMode() {
    $("authTitle").textContent =
        authMode === "login" ? "Sign in" : "Create account";

    $("authSubmit").textContent =
        authMode === "login" ? "Sign in" : "Create account";

    $("nameWrap").classList.toggle(
        "hidden",
        authMode === "login"
    );

    $("switchAuth").innerHTML =
        authMode === "login"
        ? 'New here? <a href="#">Create an account</a>'
        : 'Already registered? <a href="#">Sign in</a>';
}

function openAuth() {
    authMode = "login";
    setAuthMode();

    $("authMessage").textContent = "";
    $("authModal").classList.remove("hidden");
}

$("authBtn").onclick = async () => {
    if (token()) {
        await loadBookingHistory();
    } else {
        openAuth();
    }
};

$("switchAuth").onclick = e => {
    e.preventDefault();

    authMode = authMode === "login"
        ? "signup"
        : "login";

    $("authMessage").textContent = "";
    setAuthMode();
};

$("authForm").onsubmit = async e => {
    e.preventDefault();

    $("authMessage").textContent = "Please wait...";

    try {
        const data = await api(
            authMode === "login"
                ? "/api/login"
                : "/api/signup",
            {
                method: "POST",
                body: JSON.stringify({
                    name: $("authName").value,
                    email: $("authEmail").value,
                    password: $("authPassword").value
                })
            }
        );

        localStorage.setItem("showtime_token", data.token);

        $("authModal").classList.add("hidden");

        updateAuthUI();

        toast("Welcome to Showtime, " + data.user.name + "!");

    } catch (err) {
        $("authMessage").textContent = err.message;
    }
};


// BOOKING HISTORY

async function loadBookingHistory() {
    if (!token()) {
        openAuth();
        return;
    }

    $("historyModal").classList.remove("hidden");

    $("bookingHistory").innerHTML =
        "<p>Loading your bookings...</p>";

    try {
        const bookings = await api("/api/my-bookings");

        if (!Array.isArray(bookings) || bookings.length === 0) {
            $("bookingHistory").innerHTML =
                "<p style='padding:20px'>You have no bookings yet. Book your first movie!</p>";
            return;
        }

        $("bookingHistory").innerHTML = bookings.map(b => {
            const code = b.code || b.booking_code || "N/A";
            const movie = b.movie || b.movie_title || "Movie";
            const date = b.show_date || "N/A";
            const time = b.show_time || "N/A";
            const seats = b.seats || "N/A";
            const amount = b.amount ?? "N/A";
            const status = b.status || b.payment_status || "PENDING";

            return `
            <div style="
                border:1px solid #66503a;
                border-radius:12px;
                padding:20px;
                margin:15px 0;
                background:#211b18;
                color:#fff;
            ">
                <h3 style="color:#d6ad77;margin-bottom:12px">
                    ${movie}
                </h3>

                <p><b>Booking ID:</b> ${code}</p>
                <p><b>Date:</b> ${date}</p>
                <p><b>Showtime:</b> ${time}</p>
                <p><b>Seats:</b> ${seats}</p>
                <p><b>Amount:</b> ₹${amount}</p>

                <p style="margin-top:12px">
                    <b>Payment Status:</b>
                    <span style="color:${status === 'PAID' ? '#7ee6a0' : '#f5c46b'}">
                        ${status}
                    </span>
                </p>
            </div>`;
        }).join("");

    } catch (err) {
        $("bookingHistory").innerHTML =
            `<p class="message">${err.message}</p>`;
    }
}


// LOGOUT

$("logoutBtn").onclick = () => {
    if (confirm("Are you sure you want to log out?")) {
        localStorage.removeItem("showtime_token");

        $("historyModal").classList.add("hidden");

        updateAuthUI();

        toast("You have been logged out.");
    }
};


// CLOSE MODALS

document.querySelectorAll("[data-close]").forEach(button => {
    button.onclick = () => {
        $(button.dataset.close).classList.add("hidden");
    };
});


// SEAT BOOKING

function openBooking(id) {
    selectedMovie = movies.find(m => m.id === id);

    if (!selectedMovie) return;

    selectedSeats.clear();

    $("bookingTitle").textContent = selectedMovie.title;

    $("showDate").min = new Date().toISOString().slice(0, 10);
    $("showDate").value = $("showDate").min;

    $("bookingMessage").textContent = "";

    $("bookingModal").classList.remove("hidden");

    loadSeats();
}

$("showDate").onchange = loadSeats;
$("showTime").onchange = loadSeats;


async function loadSeats() {
    if (!selectedMovie) return;

    selectedSeats.clear();

    try {
        const query = new URLSearchParams({
            movie_id: selectedMovie.id,
            date: $("showDate").value,
            time: $("showTime").value
        });

        const data = await api("/api/booked-seats?" + query);

        const booked = new Set(data.seats);

        $("seats").innerHTML = Array.from(
            { length: 40 },
            (_, i) => {
                const n = i + 1;
                const id = "S" + n;

                return `
                <button class="seat ${booked.has(id) ? "booked" : ""}"
                    data-seat="${id}"
                    ${booked.has(id) ? "disabled" : ""}>
                    ${n}
                </button>`;
            }
        ).join("");

        document.querySelectorAll(".seat:not(.booked)").forEach(button => {
            button.onclick = () => {
                const seat = button.dataset.seat;

                if (selectedSeats.has(seat)) {
                    selectedSeats.delete(seat);
                    button.classList.remove("selected");

                } else if (selectedSeats.size < 8) {
                    selectedSeats.add(seat);
                    button.classList.add("selected");

                } else {
                    toast("Maximum 8 seats per booking.");
                }

                updateTotal();
            };
        });

        updateTotal();

    } catch (err) {
        $("bookingMessage").textContent = err.message;
    }
}


function updateTotal() {
    $("seatCount").textContent = selectedSeats.size;

    $("total").textContent =
        "₹" + selectedSeats.size * 150;
}


// PAYMENT

$("payBtn").onclick = async () => {
    if (!token()) {
        $("bookingModal").classList.add("hidden");
        openAuth();
        toast("Please sign in before booking.");
        return;
    }

    if (!selectedSeats.size) {
        $("bookingMessage").textContent =
            "Please select at least one seat.";
        return;
    }

    $("payBtn").disabled = true;

    try {
        const data = await api("/api/create-order", {
            method: "POST",
            body: JSON.stringify({
                movie_id: selectedMovie.id,
                seats: [...selectedSeats],
                date: $("showDate").value,
                time: $("showTime").value
            })
        });

        if (data.demo_mode) {
            const confirmed = confirm(
                "Razorpay test keys are not configured. Complete a DEMO payment for judging?"
            );

            if (!confirmed) return;

            const result = await api("/api/confirm-demo-payment", {
                method: "POST",
                body: JSON.stringify({
                    booking_id: data.booking_id
                })
            });

            $("bookingModal").classList.add("hidden");

            toast("Booking confirmed: " + result.booking_code);

            loadSeats();

            return;
        }

        const options = {
            key: data.key_id,
            amount: data.amount * 100,
            currency: "INR",
            name: "Showtime",
            description: selectedMovie.title + " movie tickets",
            order_id: data.razorpay_order_id,

            handler: async response => {
                try {
                    const result = await api("/api/verify-payment", {
                        method: "POST",
                        body: JSON.stringify({
                            ...response,
                            booking_id: data.booking_id
                        })
                    });

                    $("bookingModal").classList.add("hidden");

                    toast("Payment successful! " + result.booking_code);

                    loadSeats();

                } catch (err) {
                    toast(err.message);
                }
            },

            theme: {
                color: "#c89b62"
            }
        };

        new Razorpay(options).open();

    } catch (err) {
        $("bookingMessage").textContent = err.message;

    } finally {
        $("payBtn").disabled = false;
    }
};


// START APPLICATION

loadMovies();
updateAuthUI();
