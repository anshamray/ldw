const form = document.getElementById("form");

async function submitConfirmation(event) {
    event.preventDefault();

    const textInput = document.getElementById("text");
    const text = textInput.value;
    const submitBtn = form.querySelector('button[type="submit"]');

    // Disable button while submitting
    submitBtn.disabled = true;
    submitBtn.textContent = 'Wird gesendet...';

    try {
        const response = await fetch('/api/v1/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById("textInhalt").innerHTML =
                `Vielen Dank! Ihre Nachricht ist #${data.position} in der Warteschlange.`;
            form.classList.toggle("hidden");
        } else {
            alert(data.message || 'Ein Fehler ist aufgetreten.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Senden';
        }
    } catch (error) {
        alert('Verbindungsfehler. Bitte versuchen Sie es erneut.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Senden';
    }
}

function clearInput() {
    document.getElementById("text").value = "";
}

function backgroundStars() {
    for (let i = 0; i < 50; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDelay = Math.random() * 4 + 's';
        document.body.appendChild(star);
    }
}

document.addEventListener('DOMContentLoaded',() => {
    backgroundStars();
    clearInput();
});

form.addEventListener("submit", submitConfirmation);